# UKG Pro WFM

| | |
|---|---|
| Plugin ID | `ukg_pro_wfm` (repo is `plugin-ukgpro`) |
| Plugin FQN | `OMNATA__UKG_PRO_WFM` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/ukgpro/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`), all optional with defaults:
- `start_date`: earliest date to sync from.
- `schedule_forward_days`: how far ahead to read schedules.
- `workload_lookback_days`: lookback window for workload planner data.
- `timeoff_backward_days` / `timeoff_forward_days`: time off history and future horizon.
- `reprocess_window_days` / `reprocess_interval_hours`: periodic re-read window and frequency.
- `detect_deletes_via_audit` (checkbox, default false): detect deletes via audit logs.

Tuning parameters (`inbound_tuning_parameters`): `rest_batch_size`, `date_chunk_days`, `detection_window_days`.

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
- Connection requires tenant `api_url` and `token_url` (password-realm OAuth).

## Sources

- Code: `omnata-labs/plugin-ukgpro` at `src/plugin.py` (3,900+ lines; only the forms and `inbound_stream_list` were reviewed)
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/ukgpro/README.md`
- Not verified: full stream list beyond `jobs` (list continues past the reviewed section), and the numeric default values of each parameter (defined as constants elsewhere).
