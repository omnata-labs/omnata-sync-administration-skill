# Slack

| | |
|---|---|
| Plugin ID | `slack` |
| Plugin FQN | `OMNATA__SLACK` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/slack/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `start_date` (optional, text input): labelled "Start Date". It wasn't verified to have any effect; leave it unset.

**Streams**: static, single stream `conversations_list` (primary key `id`, default cursor `updated`).

**Sync strategies supported**: `Incremental` and `Full Refresh`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'slack-inbound',
    SYNC_NAME          => 'Slack to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['conversations_list'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Post Message`: custom strategy. Posts a message into a Slack channel on record create only. Does not act on update, delete or unchanged records.

**Sync parameters** (`SYNC_PARAMETERS`):
- `channel` (required, dynamic dropdown): channel to post in. The bot user must be invited to the channel for it to appear. The stored value includes metadata (`id`, `name`, `is_channel`); see the Slack section of `configure-syncs.md` for the shape.

**Field mappings** (`FIELD_MAPPINGS`): `jinja_template` (labelled "Message Template"). The template references source columns as `row['COLUMN_NAME']`.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Full worked outbound example, including the `channel` object and Jinja preview, is in `configure-syncs.md` ("Outbound Plugin: Slack").
- OAuth scopes requested: `chat:write`, `users:read.email`, `users:read`, `channels:read`.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/slack/README.md`
- Existing reference: `omnata-sync-administration-skill/references/configure-syncs.md`, section "Outbound Plugin: Slack" (consistent with this page)
- Conflict: docs say `conversations_list` is Full Refresh only; the plugin supports both Full Refresh and Incremental. Docs list the outbound strategy as "Create"; the plugin's strategy is `Post Message`.
