# Microsoft SQL Server

| | |
|---|---|
| Plugin FQN | `MONITORIAL__MSSQL` |
| Page | `mssql.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_type` (required, default `watermark`): `cdc` (Change Data Capture), `ct` (Change Tracking) or `watermark` (high watermark).
- `database` (required): the source database.
- `schema_mode` (required, default `single`): `single` or `multi`.
- `schema` (required): the source schema. It is multi-select when `schema_mode` is `multi`.
- `object_type` (required, default `table`): `table`, `view` or `both`. Shown for watermark syncs.
- `additional_where_clause` (optional): an extra filter. Watermark syncs only.
- `net_changes_only` (optional, default false): capture net changes when appending. CDC only.

**Streams**: discovered from the chosen database, schema and object type. In single schema mode the stream name is the object name, such as `Customers`. In multi schema mode it is schema, underscore, object, such as `dbo_Customers`. Primary keys come from the table's key columns. For watermark syncs the default cursor is a rowversion column, else a datetime column with modified or updated in its name, else none.

## Notes

- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
- CDC or Change Tracking must already be enabled on the source database and tables, or no streams are listed.
- Tables with no key need `STREAM_PRIMARY_KEYS` for merge. Tables with no detected cursor need `STREAM_CURSOR_FIELDS` for Incremental.
- Connectivity options are Direct, ngrok and PrivateLink.
- The tuning parameter `index_column_overrides` maps a stream name to the column used to split a table into range queries. Use it for heap tables or poorly distributed indexes. Keys must match the stream name exactly. Malformed values are ignored with a warning.
- If a CDC capture instance changes, refresh the sync's streams after the old instance is disabled. The next run picks up the new instance and does a full refresh.
