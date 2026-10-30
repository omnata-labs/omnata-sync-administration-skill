# GitHub

| | |
|---|---|
| Plugin FQN | `OMNATA__GITHUB` |
| Page | `github.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `OAuth App` and `Personal Access Token` (field `personal_access_token`, secret).
- **OAuth values**: grant type authorization code; authorization endpoint `https://github.com/login/oauth/authorize`; token endpoint `https://github.com/login/oauth/access_token`; scopes `repo`, `read:org`, `user`.
- Org streams such as `organization_members` and `organization_teams` need org read access.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `organization` (required): the org login, from a dynamic list of organisations the connection can see.
- `repository_pattern` (required, default `.*`): regex for repository names to include.
- `branch_pattern` (required, default `^main$|^master$`): regex for branch names to include.

**Streams**: static list, for example `repositories`, `commits`, `pull_requests`. `pull_request_commits` and `pull_request_events` depend on `pull_requests`.

## Notes

- One organisation per sync. Create one sync per organisation.
- GitHub rate limits are per identity (5,000 requests per hour). For large orgs, split repositories across syncs with narrower `repository_pattern` values, or stagger schedules.
