# Databricks

| | |
|---|---|
| Plugin ID | `databricks` |
| Plugin FQN | `MONITORIAL__DATABRICKS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/databricks/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `database` (required): Databricks catalog/database to read from, chosen from a dynamic list.
- `schema_mode` (required, default `single`): `single` (all objects land in one Snowflake schema) or `multi` (each source schema maps to its own Snowflake schema).
- `schema` (required): source schema. A single value in `single` mode, a multi-select list in `multi` mode.
- `additional_where_clause` (optional): extra filter applied to records, for example `column_name = value`. No semicolons, comments or DDL/DML keywords.

**Streams**: Dynamic. One stream per table or view in the selected database and schema(s), discovered from Databricks metadata. Stream name is the object name in `single` mode, and `<schema>_<object>` in `multi` mode. Objects without key columns have no source-defined primary key, so pass `STREAM_PRIMARY_KEYS` for them if merging. Cursors are never source-defined: a default cursor is suggested from date/timestamp/integer columns named like `modified`, `updated` or `created`, otherwise pass `STREAM_CURSOR_FIELDS` for incremental streams.

**Sync strategies supported**: Objects with at least one date, timestamp or integer column support `Incremental` (high watermark) and `Full Refresh`. Objects with no such column are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'databricks-inbound',
    SYNC_NAME          => 'Databricks to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name_1>', '<table_name_2>'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
        'database', '<catalog>',
        'schema_mode', 'single',
        'schema', '<schema>'
    ),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Changing `database`, `schema_mode` or `schema` changes the stream list and the stream names.
- Tuning parameters (not sync parameters): `max_concurrent_streams` (1 to 64, default 8), `max_concurrent_queries` (1 to 64, default 4), `max_records_per_query` (100K to 25M, default 1M).
- The connection needs `server_host`, `http_path`, `cloud_provider` and usually `external_storage` (storage accounts used for unloading, not needed on GCP). The external access integration must allow those storage endpoints.
- The connecting principal needs `USE CATALOG`, `USE SCHEMA` and `SELECT` on synced objects.

## Sources

- Code: `plugin-databricks` at `src/plugin.py`, `src/metadata/database_metadata.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/databricks/README.md`
- Stream names are tenant-specific, so the example uses placeholders. Value format for `schema` in `multi` mode (array) is assumed, not verified.
