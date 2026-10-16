#!/usr/bin/env python3
"""
Preview Omnata inbound storage location templates for a set of planned syncs.

Uses the same template variables and filters as the Omnata Sync Engine, so the
rendered names match what the sync engine will create. Also flags collisions,
where two streams render to the same raw or normalized table, and app-database
schemas the engine rejects.

Input (JSON file or stdin):
{
  "app_database": "OMNATA_SYNC_ENGINE",
  "plugin_id": "mssql",
  "syncs": [
    {
      "sync_slug": "bizcover-sqlserver-sales-dbo",
      "branch_name": "main",
      "sync_parameters": {"sync_type": "ct", "database": "AdventureWorks", "schema": "dbo"},
      "streams": ["Customers", "OrderLines"],
      "storage_location": { ... keys of INBOUND_STORAGE_LOCATION ... },
      "plugin_id": "mssql",        (optional, overrides the top-level plugin_id)
      "existing": true             (optional, marks an existing sync on its stored location)
    }
  ]
}
Branches: every branch of a sync renders the same template with its own
branch_name. Top-level "branches" (default ["main"]) lists the branches to render
for every sync; a sync's own "branches" list overrides it. Include a hypothetical
branch such as "test" to check that branches don't collide with main.

Optional top-level "existing_tables": ["DB.SCHEMA.TABLE", ...] lists tables and
views already in the target location (from INFORMATION_SCHEMA). Any rendered path
matching one is flagged, since the engine reuses an existing raw table silently.

Each sync may carry its own storage_location (for hard-coded values); otherwise
a top-level "storage_location" applies to all syncs except those marked existing.

Usage: python3 render_storage_location.py plan.json
"""
import json
import re
import sys
import unicodedata

from jinja2 import Environment

DEFAULTS = {
    "raw_database": None,
    "raw_schema": "INBOUND_RAW",
    "raw_object": "{{sync_slug}}_{{branch_name}}_{{stream_name}}",
    "normalized_database": None,
    "normalized_schema": "INBOUND_NORMALIZED",
    "normalized_object": "{{sync_slug}}_{{branch_name}}_{{stream_name}}",
    "normalized_column": "{{column_name}}",
}
APP_DB_SCHEMAS = {"INBOUND_RAW", "INBOUND_NORMALIZED"}


def fivetran_word_division(text: str) -> str:
    result = ""
    for i, c in enumerate(text):
        if i == 0:
            result += c.lower()
        else:
            if c.isupper() and text[i - 1].islower():
                result += "_"
            elif c.isnumeric() and text[i - 1].isalpha():
                result += "_"
            elif c.isalpha() and text[i - 1].isnumeric():
                result += "_"
            result += c.lower()
    return result


def multiple_underscores_to_single(text: str) -> str:
    return re.sub(r"_+", "_", text)


def transliterate(text: str) -> str:
    try:
        import unidecode  # same library the engine uses

        return unidecode.unidecode(text)
    except ImportError:
        # Close approximation when unidecode isn't installed
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def prepend_starting_number_with_underscore(text: str) -> str:
    if len(text) == 0:
        return text
    if text[0].isnumeric():
        return f"_{text}"
    return text


def environment() -> Environment:
    env = Environment()
    env.filters["fivetran_word_division"] = fivetran_word_division
    env.filters["multiple_underscores_to_single"] = multiple_underscores_to_single
    env.filters["transliterate"] = transliterate
    env.filters["prepend_starting_number_with_underscore"] = prepend_starting_number_with_underscore
    return env


def render(env, template, variables):
    return env.from_string(f"{template}").render(**variables)


def main():
    plan = json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    env = environment()
    app_db = plan.get("app_database", "OMNATA_SYNC_ENGINE")
    shared_location = plan.get("storage_location", {})
    seen = {"raw": {}, "normalized": {}}
    problems = []
    rows = []
    # Schemas the planned (non-existing) syncs need, and what lands in each
    needed = {}
    # Exact-case match, since rendered names are quoted identifiers
    existing_tables = {tuple(t.split(".")): t for t in plan.get("existing_tables", [])}

    for sync in plan["syncs"]:
        # Existing syncs keep their stored location, so the shared template doesn't apply
        shared = {} if sync.get("existing") else shared_location
        location = {**DEFAULTS, **shared, **sync.get("storage_location", {})}
        for key in ("raw_database", "normalized_database"):
            if not location[key]:
                location[key] = app_db
        if "branches" in sync:
            branches = sync["branches"]
        elif sync.get("branch_name"):
            branches = [sync["branch_name"]]
        else:
            branches = plan.get("branches", ["main"])
        for branch, stream in ((b, st) for b in branches for st in sync["streams"]):
            variables = {
                "stream_name": stream,
                "sync_slug": sync["sync_slug"],
                "branch_name": branch,
                "sync_parameters": sync.get("sync_parameters", {}),
                "plugin_id": sync.get("plugin_id", plan.get("plugin_id", "mssql")),
            }
            row = {"sync_slug": sync["sync_slug"], "branch": branch, "stream": stream}
            label = f"{sync['sync_slug']}/{branch}/{stream}"
            if sync.get("existing"):
                row["existing"] = True
            for table_type in ("raw", "normalized"):
                path = tuple(
                    render(env, location[f"{table_type}_{part}"], variables)
                    for part in ("database", "schema", "object")
                )
                row[table_type] = '"{}"."{}"."{}"'.format(*path)
                if not sync.get("existing") and path[0].lower() != app_db.lower():
                    needed.setdefault((path[0], path[1]), set()).add(
                        "tables" if table_type == "raw" else "views"
                    )
                if path[0].replace('"', "").lower() == app_db.lower() and path[1] not in APP_DB_SCHEMAS:
                    problems.append(
                        f"{label}: {table_type} schema {path[1]} is in the Omnata app "
                        f"database, which only allows INBOUND_RAW / INBOUND_NORMALIZED"
                    )
                # Names are quoted, so collisions are exact-case matches
                key = path
                if key in seen[table_type]:
                    problems.append(
                        f"COLLISION ({table_type}): {label} and "
                        f"{seen[table_type][key]} both render to {row[table_type]}"
                    )
                else:
                    seen[table_type][key] = f"{label}"
                if not sync.get("existing") and path in existing_tables:
                    problems.append(
                        f"EXISTING OBJECT ({table_type}): {label} renders to "
                        f"{row[table_type]}, which already exists in the account"
                    )
                if any(c.islower() for c in "".join(path)):
                    row.setdefault("notes", []).append(
                        f"{table_type} name contains lowercase characters, so it will be a case-sensitive quoted identifier"
                    )
            column_example = render(env, location["normalized_column"], {"column_name": sync.get("sample_column", "CustomerID")})
            row["sample_column"] = column_example
            rows.append(row)

    schemas = [
        {"database": db, "schema": sc, "holds": sorted(kinds)}
        for (db, sc), kinds in sorted(needed.items())
    ]
    print(json.dumps({"rendered": rows, "schemas_needed": schemas, "problems": problems}, indent=2))


if __name__ == "__main__":
    main()
