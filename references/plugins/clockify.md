# Clockify

| | |
|---|---|
| Plugin FQN | `MONITORIAL__CLOCKIFY` |
| Page | `clockify.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- `domain_prefix` is the regional API prefix (for example `euc1`, `use2`, `euw2`, `apse2`; default `api`). It must match the workspace region or API calls fail.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `workspaces` (required, multi-select): the Clockify workspace IDs to retrieve data for. Values are workspace IDs, not names.

**Streams**: a static list (e.g. `users`, `projects`, `time_entries`). Some child streams are populated from a parent stream, so include the parent in the same sync.

## Notes

- `time_entries` is fetched per user, so include `users` in the same sync.
- `time_entries` also processes deletes from Clockify.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
