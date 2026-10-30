# Airtable

| | |
|---|---|
| Plugin FQN | `OMNATA__AIRTABLE` |
| Page | `airtable.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `base` (required in practice, since streams can't be listed without it): the Airtable base ID to sync from.

**Streams**: dynamic, one stream per table in the selected base, named by the table name.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `base`: the target base ID.
- `table_name`: the target table name (depends on `base`).

**Field mappings**: `field_mapping_selector`, built from the chosen table's fields. Formula, rollup, lookup, system timestamp and multi-value fields are excluded. The table's primary field is a required mapping and is the upsert key.

**Before running**: `Replace` replaces the target table's contents in full, removing records not in the Snowflake data. Records removed from Airtable can't be recovered by Omnata. Show the user the target base and table and wait for their explicit yes; don't treat an unclear reply as confirmation.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Table names are used as stream names, so they can contain spaces and mixed case.
- Writes use Airtable batch upsert with typecast enabled.
