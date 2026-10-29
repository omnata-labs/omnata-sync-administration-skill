# QuestDB

| | |
|---|---|
| Plugin ID | `questdb` |
| Plugin FQN | `OMNATA__QUESTDB` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/questdb/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`. `max_concurrent_streams` is a tuning parameter.

**Streams**: Dynamic. One stream per QuestDB table, discovered via `tables()` and `table_columns()`, named by table name. Primary key is the table's upsert key columns; tables without upsert keys have no source-defined primary key and need `STREAM_PRIMARY_KEYS`. Default cursor is the table's designated timestamp.

**Sync strategies supported**: Tables with a designated timestamp support `Incremental` and `Full Refresh`. Tables without one support `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'questdb-inbound',
    SYNC_NAME          => 'QuestDB to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name_1>', '<table_name_2>'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Connectivity can be direct, ngrok or PrivateLink; set on the connection.
- `timestamp_ns` values are truncated to microseconds in typed columns; the original is kept in `RECORD_DATA`.
- Initial load is the heaviest; reduce `max_concurrent_streams` (default 8) to limit source load.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/questdb/README.md`
- No real table names are known from code; the example uses placeholders.
