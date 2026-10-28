# UKG Pro WFM

| | |
|---|---|
| Plugin ID | `ukg_pro_wfm` (repo is `plugin-ukgpro`) |
| Plugin FQN | `OMNATA__UKG_PRO_WFM` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/ukgpro/README.md` |

## Connection

Follow `configure-connections.md`. Two methods, both OAuth password grant (no browser flow):
- `OAuth (Password-Realm)`: `api_url` (tenant host, e.g. `<tenant>.npr.mykronos.com`), `token_url` (e.g. `https://welcome-us.ukg.net`), `client_id`, `client_secret` (secret), `username`, `password` (secret), `audience`, `realm`. Token is posted to `<token_url>/oauth/token`.
- `OAuth (Password)`: UKG's documented WFM flow, posts `grant_type=password` to the tenant host. Fields: `api_url`, `client_id`, `client_secret` (secret), `username`, `password` (secret). Use when the tenant's identity host or realm is unknown.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`), all optional with defaults:
- `start_date` (default `2022-01-01`): start date for the initial full refresh; incremental syncs ignore it.
- `schedule_forward_days` (default 56): how far ahead to read schedules.
- `workload_lookback_days` (default 56): lookback window for workload planner data.
- `timeoff_backward_days` / `timeoff_forward_days` (defaults 365 / 180): time off history and future horizon.
- `reprocess_window_days` / `reprocess_interval_hours` (defaults 7 / 12): periodic full re-read of `timecards` and `timecard_spans`. Window capped at 35; set window to 0 to disable (interval cannot be 0).
- `detect_deletes_via_audit` (checkbox, default false): detect deletes via audit logs.

Tuning parameters (`inbound_tuning_parameters`): `rest_batch_size` (default 500), `date_chunk_days` (default 30), `detection_window_days`, `workload_read_timeout_seconds` (default 180). If `workload_planner` fails with read timeouts, raise `workload_read_timeout_seconds`; timed-out batches are already retried one location at a time before failing.

**Streams**: static list. Representative: `employees`, `timecards`, `timecard_exceptions`, `timecard_spans` (both depend on `timecards`), `schedules`, `workload_planner`, `timeoff_requests`, `jobs`. All define primary key `id` and a default cursor.

**Sync strategies supported**: `timecards`, `schedules`, `workload_planner` and timecard children support `Incremental` and `Full Refresh`. `employees`, `timeoff_requests` and `jobs` are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'ukg_pro_wfm-inbound',
    SYNC_NAME          => 'UKG Pro WFM to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['employees', 'timecards', 'schedules'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Sync parameters change API date windows; see the "Sync options" table in the docs for defaults and effects.
- `OAuth (Password-Realm)` needs network access to both the `api_url` and `token_url` hosts; `OAuth (Password)` only the `api_url` host.
- Transient UKG errors are retried on all streams. A read that still fails after retries fails the stream (it is no longer skipped); this applies to `employees`, the timecard audit, and timecard and schedule change detection. Treat such failures as UKG-side or connectivity issues and rerun.
- Consumer UDTF `DATA_MULTI_READ(CONNECTION_PARAMETERS, SELECT_ARRAY, FROM_OBJECT, WHERE_ARRAY, RESULT_COUNT, RESULT_INDEX, OPTIONS, SORT_BY, GROUP_BY)` calls UKG `commons/data/multi_read` directly; arguments after `FROM_OBJECT` default to NULL. Returns one row per child: `RAW_CHILD` (OBJECT), `METADATA` (OBJECT). Example `SELECT_ARRAY`: `[{"key": "EMP_COMMON_FULL_NAME"}]`; `FROM_OBJECT` holds the view plus `employeeSet` or `locationSet`.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/ukgpro/README.md`
- Not verified: consumer schema containing `DATA_MULTI_READ`.
- Not verified: numeric default of `detection_window_days` (`AUDIT_MAX_RANGE_DAYS`, not traced).
