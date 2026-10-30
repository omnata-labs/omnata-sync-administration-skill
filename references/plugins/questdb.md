# QuestDB

| | |
|---|---|
| Plugin FQN | `OMNATA__QUESTDB` |
| Page | `questdb.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: one per QuestDB table, named by table name. Tables without upsert keys need `STREAM_PRIMARY_KEYS`. Tables without a designated timestamp support Full Refresh only.

## Notes

- Connectivity (direct, ngrok or PrivateLink) is set on the connection.
- `timestamp_ns` values are truncated to microseconds in typed columns. The original value is kept in `RECORD_DATA`.
