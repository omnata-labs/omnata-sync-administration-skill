# Databricks

| | |
|---|---|
| Plugin FQN | `MONITORIAL__DATABRICKS` |
| Page | `databricks.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Fields**: `server_host`, `http_path`, `cloud_provider`, and usually `external_storage` (storage accounts used for unloading; not needed on GCP).
- **Before you start**: the connecting principal needs `USE CATALOG`, `USE SCHEMA` and `SELECT` on synced objects. The external access integration must allow the storage endpoints.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `database` (required): the Databricks catalog to read from, chosen from a dynamic list.
- `schema_mode` (required, default `single`): `single` lands all objects in one Snowflake schema. `multi` maps each source schema to its own Snowflake schema.
- `schema` (required): the source schema. One value in `single` mode, a multi-select list in `multi` mode.
- `additional_where_clause` (optional): an extra record filter, for example `column_name = value`. No semicolons, comments or DDL/DML keywords.

**Streams**: dynamic, one per table or view in the selected schemas. The stream name is the object name in `single` mode and `<schema>_<object>` in `multi` mode. Objects without key columns have no primary key, so pass `STREAM_PRIMARY_KEYS` when merging. Cursors are never source-defined, so pass `STREAM_CURSOR_FIELDS` for incremental streams unless a default is suggested.

## Notes

- Changing `database`, `schema_mode` or `schema` changes the stream list and the stream names.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
