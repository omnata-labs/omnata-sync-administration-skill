# Aircall

| | |
|---|---|
| Plugin ID | `aircall` |
| Plugin FQN | `OMNATA__AIRCALL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/aircall/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `lookback_days` (optional): days of call history fetched on the first sync. Capped by the plugin because Aircall only keeps about 6 months.

**Streams**: Static list, gated by the connection parameter `ai_assist_package`. Standard streams include `users`, `teams`, `numbers`, `tags`, `contacts`, `calls`, plus child streams such as `contact_phone_numbers` and `call_comments` that depend on a parent. Conversation Intelligence streams (`call_ci_transcriptions`, `call_ci_summaries`, `call_ci_sentiments` and others) appear only for AI Assist or AI Assist Pro packages. All streams have a source-defined primary key.

**Sync strategies supported**: Reference streams (`users`, `teams`, `numbers`, `tags`, `webhooks`) are `Full Refresh` only. `contacts` (cursor `updated_at`) and `calls` (cursor `started_at`) and their children support `Incremental`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'aircall-inbound',
    SYNC_NAME          => 'Aircall to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['users', 'contacts', 'calls', 'call_comments'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('lookback_days', '90'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Child streams declare `depends_on_stream`; include the parent (`contacts` or `calls`) when selecting them.
- If CI streams are missing, check the connection's `ai_assist_package` value rather than the sync.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/aircall/README.md`
- Exact lookback default and cap values not copied; cursor and strategy for every CI stream not individually verified.
