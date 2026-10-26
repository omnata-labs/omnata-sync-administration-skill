# Microsoft SQL Server

| | |
|---|---|
| Plugin ID | `mssql` |
| Plugin FQN | `MONITORIAL__MSSQL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/mssql/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_type` (required, default `watermark`): `cdc` (Change Data Capture), `ct` (Change Tracking) or `watermark` (Full Refresh / Incremental by high watermark).
- `database` (required): the source database.
- `schema_mode` (required, default `single`): `single` or `multi`.
- `schema` (required): the source schema, multi-select when `schema_mode` is `multi`.
- `object_type` (required, default `table`): `table`, `view` or `both`. Shown for watermark syncs.
- `additional_where_clause` (optional): extra filter, Full Refresh / Incremental only.
- `net_changes_only` (optional, default false): CDC only, capture net changes when appending.

**Streams**: discovered dynamically from the database metadata for the chosen database, schema and object type. In single schema mode the stream name is the object name (for example `Customers`); in multi schema mode it is `<schema>_<object>` (for example `dbo_Customers`). Primary keys come from the table's key columns; objects without key columns have no source-defined primary key. For watermark syncs the default cursor is a rowversion column, else a datetime column containing "modified" or "updated", else none.

**Sync strategies supported**: CDC and CT streams are Incremental only. Watermark streams support Incremental and Full Refresh when a datetime or rowversion column exists, otherwise Full Refresh only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'mssql-inbound',
    SYNC_NAME          => 'Microsoft SQL Server to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name>', '<other_table_name>'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('sync_type', 'watermark', 'database', '<database>', 'schema_mode', 'single', 'schema', 'dbo', 'object_type', 'table'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- CDC or Change Tracking must already be enabled on the source database and tables for `cdc` / `ct` to list streams.
- Watermark tables without a key need `STREAM_PRIMARY_KEYS` for merge; those without a detected cursor need `STREAM_CURSOR_FIELDS` for Incremental.
- Connectivity options are Direct, ngrok and PrivateLink.
- Tuning parameters (`sync_tuning_parameters`, not sync parameters): `isolation_level` (`server` default, `committed`, `uncommitted`, `repeatable`), `max_concurrent_streams` (1 to 64, default 8), `max_concurrent_queries` (1 to 64, default 4), `max_records_per_query` (100K to 25M, default 1M), and optional `index_column_overrides`.
- `index_column_overrides` is a JSON string mapping stream name to the column used to split a table into range queries, for example `'{"Customers": "CustomerID"}'` (default `'{}'`). Use it for heap tables or poorly distributed indexes. Keys must match the stream name exactly (so `<schema>_<object>` in multi schema mode). Malformed JSON is logged as a warning and ignored.
- CDC capture instance changes (for example a second instance to add columns): after the old instance is disabled, refresh the sync's streams; the next run detects the new instance, resets LSN state and does a full refresh. If the stored instance no longer exists, the plugin falls back to an available instance for that table.
- An `outbound_configuration_form` exists in code but the manifest registers no outbound strategies.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/mssql/README.md`
- Not verified: the FQN (derived from `developer_id='monitorial'`), and the exact stored format for a multi-select `schema` value.
