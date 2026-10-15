# Mailgun

| | |
|---|---|
| Plugin ID | `mailgun` |
| Plugin FQN | `OMNATA__MAILGUN` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/mailgun/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: static, a single stream `logs`. It has source-defined primary key `id` and default cursor `@timestamp`, so no `STREAM_PRIMARY_KEYS` / `STREAM_CURSOR_FIELDS` are needed.

**Sync strategies supported**: `logs` supports both Incremental and Full Refresh.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'mailgun-inbound',
    SYNC_NAME          => 'Mailgun to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['logs'],
    SYNC_STRATEGY      => 'Incremental'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- The connection form requires `api_key` and `region`. The region determines the API host, so a wrong region surfaces at connection time, not sync time.
- `FormFieldMappingSelector` is imported in `plugin.py` but unused; there is no outbound support.

## Sources

- Code: `omnata-labs/plugin-mailgun` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/mailgun/README.md` (agrees: inbound only).
- No gaps identified.
