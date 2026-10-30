# PostgreSQL

| | |
|---|---|
| Plugin FQN | `MONITORIAL__POSTGRESQL` |
| Page | `postgresql.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_type` (required): only option is `watermark`, the default.
- `object_type` (required): `table` (default) or `view`. Changes the stream list.
- `database` (required): the database to read schemas from.
- `schema` (required): the schema whose tables or views become streams.
- `additional_where_clause` (optional): a SQL filter applied to all streams, written without WHERE or AND.

**Streams**: one per table or view in the chosen database and schema, named by the bare object name (e.g. `orders`, not `public.orders`). Views and tables without a key need `STREAM_PRIMARY_KEYS`. Streams with no detected cursor need `STREAM_CURSOR_FIELDS` for incremental.

## Notes

- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
- Connectivity (direct, ngrok or PrivateLink) is set on the connection, not the sync.
- One schema per sync. Use separate syncs for multiple schemas.
- The stored format of `database` and `schema` (plain string or option object) is unconfirmed. Copy it from a UI-created sync if unsure.
