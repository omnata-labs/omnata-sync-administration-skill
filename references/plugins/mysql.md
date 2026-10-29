# MySQL

| | |
|---|---|
| Plugin ID | `mysql` |
| Plugin FQN | `OMNATA__MYSQL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/mysql/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `object_type` (required, default `table`): `table` or `view`.
- `database` (required): the source database.

**Streams**: discovered dynamically from the tables (or views) in the chosen database. The stream name is the bare table name (for example `orders`), with no schema prefix. Primary keys come from the table's key columns; tables without keys have no source-defined primary key. The default cursor is the first date, datetime or timestamp column whose name contains `modified`, `updated`, `update`, `created` or `create`; otherwise none. The cursor is not source-defined, so it can be overridden.

**Sync strategies supported**: every stream lists Incremental and Full Refresh.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'mysql-inbound',
    SYNC_NAME          => 'MySQL to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name>', '<other_table_name>'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('object_type', 'table', 'database', '<database>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Tables without keys need `STREAM_PRIMARY_KEYS` for merge. Tables without a detected cursor column need `STREAM_CURSOR_FIELDS` for Incremental.
- Tuning parameters (not sync parameters): `max_concurrent_streams` (1 to 64), `jdbcSetFetchSize` (100 to 100,000) and optional `cursor_default`, a starting cursor value for high watermark streams.
- Outbound syncs are not supported.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/mysql/README.md`
- Not verified: default values for the tuning parameters.
