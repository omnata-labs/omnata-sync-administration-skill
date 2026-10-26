# GitHub

| | |
|---|---|
| Plugin ID | `github` |
| Plugin FQN | `OMNATA__GITHUB` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/github/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `organization` (required): dropdown populated dynamically from the organisations visible to the connection. Value is the org login.
- `repository_pattern` (required): regular expression for repository names to include. Default `.*`.
- `branch_pattern` (required): regular expression for branch names to include. Default `^main$|^master$`.

**Streams**: static list of ten streams. Representative: `repositories`, `commits`, `pull_requests`, `pull_request_comments`, `branches`, `organization_members`. `pull_request_commits` and `pull_request_events` depend on `pull_requests`. All streams have a source-defined primary key. `branches`, `organization_members`, `organization_teams` and `organizations` have no default cursor field.

**Sync strategies supported**: `commits`, `pull_requests`, `pull_request_comments`, `pull_request_commits`, `pull_request_events` and `repositories` support `Incremental` and `Full Refresh`. `branches`, `organization_members`, `organization_teams` and `organizations` are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'github-inbound',
    SYNC_NAME          => 'GitHub to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['repositories', 'commits', 'pull_requests'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'organization', '<org_login>',
                            'repository_pattern', '.*',
                            'branch_pattern', '^main$|^master$'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- One organisation per sync. To cover multiple organisations, create one sync each.
- GitHub rate limits are per identity (5,000 requests/hour for PAT or OAuth tokens). For large orgs, split repositories across syncs with narrower `repository_pattern` values or stagger schedules.
- Connection methods: "OAuth App" (authorization code; endpoints `https://github.com/login/oauth/authorize` and `https://github.com/login/oauth/access_token`, scopes `repo`, `read:org`, `user`) and "Personal Access Token" (`personal_access_token`, secret). Org streams (`organization_members`, `organization_teams`) need org read access.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/github/README.md`
- Docs page contains an older stream list (four streams) alongside the full ten-stream table. Code matches the ten-stream table.
