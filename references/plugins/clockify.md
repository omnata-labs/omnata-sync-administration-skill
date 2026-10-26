# Clockify

| | |
|---|---|
| Plugin ID | `clockify` |
| Plugin FQN | `MONITORIAL__CLOCKIFY` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/clockify/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `workspaces` (required, multi-select): Clockify workspace IDs to retrieve data for. Options come from the `/workspaces` endpoint (value is the workspace `id`).

**Streams**: Static list defined in code (does not depend on sync parameters). Representative streams: `workspaces`, `users`, `projects`, `clients`, `tags`, `time_entries`, `approval_requests`, `assignments`, `expenses`, `invoices`. Several child streams depend on a parent and are populated from it (for example `user_settings` and `user_memberships` from `users`, `tasks` and `project_memberships` from `projects`, `time_entry_custom_field_values` from `time_entries`). All streams have a source-defined primary key (mostly `workspaceId` + `id`).

**Sync strategies supported**: `time_entries`, `approval_requests` and `assignments` (and children that inherit from them) support `Incremental` and `Full Refresh` with source-defined cursors. All other streams are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'clockify-inbound',
    SYNC_NAME          => 'Clockify to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['workspaces', 'users', 'projects', 'clients', 'time_entries'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
        'workspaces', ARRAY_CONSTRUCT('<workspace_id>')
    ),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- `workspaces` values are Clockify workspace IDs, not names.
- `time_entries` is fetched per user, so include `users` in the same sync.
- The connection's `domain_prefix` (regional prefix such as `euc1`, `use2`, `euw2`, `apse2`, default `api`) must match the workspace region or API calls fail.
- `time_entries` also processes deletes via the Clockify deleted-entities API.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/clockify/README.md`
- Exact stored value format for the multi-select `workspaces` parameter (array of IDs) is assumed, not verified.
