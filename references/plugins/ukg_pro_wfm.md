# UKG Pro WFM

| | |
|---|---|
| Plugin FQN | `OMNATA__UKG_PRO_WFM` |
| Page | `ukg_pro_wfm.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

> **Warning: credentials sent to UKG.** The `client_secret` and `password` are sent over the network to UKG's token endpoint on every token request. Have the user enter them in the Omnata UI, where they're stored as Snowflake secrets and stay out of chat and query history.

Follow `configure-connections.md`. Both methods use the OAuth password grant, with no browser flow.
- `OAuth (Password-Realm)`: `api_url` (tenant host), `token_url`, `client_id`, `client_secret` (secret), `username`, `password` (secret), `audience`, `realm`. The token is posted to the token URL at `/oauth/token`.
- `OAuth (Password)`: UKG's documented WFM flow, posted to the tenant host. Fields: `api_url`, `client_id`, `client_secret` (secret), `username`, `password` (secret). Use it when the tenant's identity host or realm is unknown.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`), all optional with defaults:
- `start_date` (default `2022-01-01`): start date for the initial full refresh. Incremental syncs ignore it.
- `schedule_forward_days` (default 56): how far ahead to read schedules.
- `workload_lookback_days` (default 56): lookback window for workload planner data.
- `timeoff_backward_days` and `timeoff_forward_days` (defaults 365 and 180): time off history and future horizon.
- `reprocess_window_days` and `reprocess_interval_hours` (defaults 7 and 12): periodic full re-read of `timecards` and `timecard_spans`. The window is capped at 35. Set the window to 0 to disable; the interval can't be 0.
- `detect_deletes_via_audit` (default false): detect deletes via audit logs.

**Streams**: static list, e.g. `employees`, `timecards`, `schedules`. `timecard_exceptions` and `timecard_spans` depend on `timecards`.

## Notes

- If `workload_planner` fails with read timeouts, raise the `workload_read_timeout_seconds` tuning parameter (default 180).
- `OAuth (Password-Realm)` needs network access to both the API and token hosts. `OAuth (Password)` needs only the API host.
