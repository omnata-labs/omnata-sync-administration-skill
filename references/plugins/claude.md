# Claude

| | |
|---|---|
| Plugin FQN | `OMNATA__CLAUDE` |
| Page | `claude.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- **Methods**: API Keys, with `compliance_access_key` and `admin_api_key` (both secrets, both optional, at least one needed). The stream list and the sync parameters depend on which keys are set.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): only present when the connection has an Admin API key. With only a Compliance Access Key there are none, pass `OBJECT_CONSTRUCT()`.
- `usage_report_bucket_width` (optional, default `1d`): time granularity for the report streams. Values `1d`, `1h`, `1m`.
- `usage_report_grouping` (optional, multi-select, default `api_key_id,workspace_id,model,service_tier`): grouping dimensions for `usage_report`. Other options include `context_window`, `inference_geo`, `account_id` and `service_account_id`. Empty means one aggregate row per bucket. The stored format (comma-separated string or array) isn't verified, so copy it from a UI-created sync if unsure.

**Streams**: static list, gated by the keys on the connection. Compliance key streams include `activities` and `user_chats`. Admin key streams include `usage_report` and `cost_report`. Several are child streams (e.g. `user_chats` depends on `organization_users`), so include the parent in the same sync.

## Notes

- Minute granularity with many grouping dimensions can produce millions of rows per day.
- Different granularities need separate syncs.
