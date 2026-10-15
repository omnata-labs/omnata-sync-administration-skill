# PostgreSQL

| | |
|---|---|
| Plugin ID | `postgresql` |
| Plugin FQN | `MONITORIAL__POSTGRESQL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/postgresql/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_type` (required): only option is `watermark` (Full Refresh / Incremental high watermark), the default.
- `object_type` (required): `table` (default) or `view`. Changes the stream list.
- `database` (required): database to read schemas from.
- `schema` (required): schema whose tables or views become streams.
- `additional_where_clause` (optional): SQL filter applied to all streams, without `WHERE`/`AND`.

**Streams**: Dynamic. One stream per table or view in the selected `database` and `schema`, named by the bare object name (for example `orders`, not `public.orders`). Primary key is the object's key columns; objects with no key (all views, keyless tables) have no source-defined primary key and need `STREAM_PRIMARY_KEYS`. Default cursor is `xmin` for tables, otherwise a timestamp column whose name contains modified/updated/created, or none.

**Sync strategies supported**: All streams offer `Incremental` and `Full Refresh`. Streams with no detected cursor need `STREAM_CURSOR_FIELDS` for incremental.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'postgresql-inbound',
    SYNC_NAME          => 'PostgreSQL to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name_1>', '<table_name_2>'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('sync_type', 'watermark', 'object_type', 'table', 'database', '<database>', 'schema', '<schema>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Developer is Monitorial, not Omnata, so the FQN prefix differs.
- Connectivity can be direct, ngrok or PrivateLink; set on the connection, not the sync.
- One schema per sync. Use separate syncs for multiple schemas.
- Initial backfill is the heaviest load on the source; tune `max_concurrent_streams` (tuning parameter, default 8).

## Sources

- Code: `omnata-labs/plugin-postgresql` at `src/plugin.py`, `src/metadata/database_metadata.py`, `src/queries/hwm_queries.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/postgresql/README.md`
- Whether dropdown values (`database`, `schema`) must be stored as plain strings or option objects was not verified. Copy from a UI-created sync if unsure.
