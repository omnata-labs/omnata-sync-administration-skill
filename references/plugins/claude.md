# Claude

| | |
|---|---|
| Plugin ID | `claude` |
| Plugin FQN | `OMNATA__CLAUDE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/claude/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): Only present when the connection has an Admin API key. With a Compliance Access Key only, there are none, pass `OBJECT_CONSTRUCT()`.
- `usage_report_bucket_width` (optional, default `1d`): time granularity for the report streams. Values `1d`, `1h`, `1m`.
- `usage_report_grouping` (optional, multi-select, default `api_key_id,workspace_id,model,service_tier`): grouping dimensions for `usage_report`. Options: `api_key_id`, `workspace_id`, `model`, `service_tier`, `context_window`, `inference_geo`, `account_id`, `service_account_id`. Empty means one aggregate row per bucket.

**Streams**: Static list, gated by which keys are on the connection.
- Compliance Access Key: `activities`, `organizations`, `organization_users`, `organization_roles`, `groups`, `group_members`, `projects`, `project_attachments`, `user_chats`.
- Admin API Key: `admin_users`, `workspaces`, `api_keys`, `invites`, `rate_limits`, `usage_report`, `cost_report`, `claude_code_usage_report`.

All streams have a source-defined primary key. Several are child streams that depend on a parent (for example `organization_users` on `organizations`, `user_chats` on `organization_users`), so include the parent in the same sync.

**Sync strategies supported**: `activities`, `usage_report`, `cost_report` and `claude_code_usage_report` support `Incremental` and `Full Refresh` with source-defined cursors. All other streams are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'claude-inbound',
    SYNC_NAME          => 'Claude to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['workspaces', 'api_keys', 'usage_report', 'cost_report', 'claude_code_usage_report'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
        'usage_report_bucket_width', '1d',
        'usage_report_grouping', 'api_key_id,workspace_id,model,service_tier'
    ),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- The connection has one method, API Keys, with `compliance_access_key` and `admin_api_key` (both optional, at least one needed). The stream list and the presence of sync parameters both depend on which keys are set.
- Minute granularity combined with many grouping dimensions can produce millions of rows per day. Different granularities need separate syncs.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/claude/README.md`
- The stored value format of the multi-select `usage_report_grouping` (comma-separated string or array) was not verified; copy from a UI-created sync if unsure. Docs state `cost_report` shares the granularity setting; not separately verified.
