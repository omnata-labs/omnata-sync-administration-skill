# MySQL

| | |
|---|---|
| Plugin FQN | `OMNATA__MYSQL` |
| Page | `mysql.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `object_type` (required, default `table`): `table` or `view`.
- `database` (required): the source database.

**Streams**: discovered from the tables or views in the chosen database. The stream name is the bare table name, with no schema prefix. Primary keys come from the table's key columns. The default cursor is the first date or timestamp column with modified, updated or created in its name. The cursor isn't source-defined, so you can override it.

## Notes

- Tables with no key need `STREAM_PRIMARY_KEYS` for merge. Tables with no detected cursor need `STREAM_CURSOR_FIELDS` for Incremental.
- The tuning parameter `cursor_default` sets a starting cursor value for high watermark streams.
