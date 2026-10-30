# Aircall

| | |
|---|---|
| Plugin FQN | `OMNATA__AIRCALL` |
| Page | `aircall.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `lookback_days` (optional): days of call history fetched on the first sync. Capped by the plugin, because Aircall only keeps about 6 months.

**Streams**: static list, gated by the connection parameter `ai_assist_package`. Conversation Intelligence streams (e.g. `call_ci_transcriptions`) appear only for the AI Assist or AI Assist Pro packages.

## Notes

- Child streams (e.g. `call_comments`) depend on a parent. Include the parent (`contacts` or `calls`) when selecting them.
- If CI streams are missing, check the connection's `ai_assist_package` value, not the sync.
