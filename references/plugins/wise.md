# Wise

| | |
|---|---|
| Plugin ID | `wise` |
| Plugin FQN | `OMNATA__WISE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/wise/README.md` (title only) |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `profile_id` (required, dynamic dropdown): the Wise profile to read transactions for.

**Streams**: static, single stream `transactions` (primary key `transactionId`, default cursor `date`). No JSON schema is supplied (`json_schema=None`).

**Sync strategies supported**: `Incremental` and `Full Refresh`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'wise-inbound',
    SYNC_NAME          => 'Wise to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['transactions'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('profile_id', '<profile_id>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- One profile per sync. Create separate syncs for multiple profiles.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/wise/README.md` contains only a heading
- Not verified: stored value format for `profile_id` (ID string vs object with metadata).
