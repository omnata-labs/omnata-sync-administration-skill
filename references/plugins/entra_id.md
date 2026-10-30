# Microsoft Entra ID

| | |
|---|---|
| Plugin FQN | `DATA_ENGINEERS__ENTRA_ID` |
| Page | `entra_id.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- **Before you start**: the Entra app registration needs Microsoft Graph application permissions: `User.Read.All` (user streams), `Group.Read.All` (groups) and `GroupMember.Read.All` (group memberships). Missing permissions make the matching streams fail.

## Inbound

> **Warning: personal data.** Before creating the sync, note that it copies personal directory data (user names, email addresses, group memberships, licence assignments) into Snowflake. Tell the user, confirm they're allowed to copy it, and recommend restricting who can query the normalized views.

**Sync parameters** (`SYNC_PARAMETERS`):
- `max_concurrent_streams` (required, 1 to 10, default 5): the maximum number of streams processed at once. It's the main lever for Graph API throttling.

**Streams**: a static list (e.g. `users`, `groups`, `user_group_memberships`). Primary keys and cursors are source-defined, so no overrides should be needed.

## Notes

- Every run re-pulls the full directory. If change history matters, historise downstream (SCD Type 2).
- The developer is Monitorial, so the FQN prefix is `DATA_ENGINEERS`, not `OMNATA`.
