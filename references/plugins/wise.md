# Wise

| | |
|---|---|
| Plugin FQN | `OMNATA__WISE` |
| Page | `wise.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `profile_id` (required): the Wise profile to read transactions for.

**Streams**: a single static stream, `transactions`.

## Notes

- One profile per sync. Create separate syncs for multiple profiles.
