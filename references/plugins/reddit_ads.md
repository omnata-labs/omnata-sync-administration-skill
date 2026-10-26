# Reddit Ads

| | |
|---|---|
| Plugin ID | `reddit_ads` |
| Plugin FQN | `OMNATA__REDDIT_ADS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/reddit_ads/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required, multi-select): Ad Accounts to sync, options fetched from Reddit.
- `reporting_mode` (required): Standard (default) or Custom. Changes the stream list.
- `time_zone_id` (optional): time zone for report day aggregation. Blank means UTC.
- `backfill_days` (optional): days of history on first sync of a performance report (docs: default 90, max 730).
- `restatement_days` (optional): trailing days re-read on each later run (docs: default 30).
- `custom_breakdowns` (required in Custom mode): breakdowns for the custom report.
- `custom_fields` (required in Custom mode): report columns for the custom report.

**Streams**: Standard mode is a static catalog: entity streams (`businesses`, `ad_accounts`, `campaigns`, `ad_groups`, `ads`, `funding_instruments`), metric streams (for example `campaign_performance`, `ad_performance`, `country_performance`) and conversion streams (for example `campaign_conversions`). Custom mode produces a single stream built from the selected breakdowns and fields; it lists nothing until both are set. All streams have source-defined primary keys (composite for report streams).

**Sync strategies supported**: Metric and conversion report streams support `Incremental` and `Full Refresh`. Entity streams are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'reddit_ads-inbound',
    SYNC_NAME          => 'Reddit Ads to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['campaigns', 'ads', 'campaign_performance', 'ad_performance'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('ad_accounts', ['<ad_account_id>'], 'reporting_mode', '<standard_mode_value>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- One Custom report per sync. Multiple custom reports need multiple syncs.
- Ad Account IDs take the form `a2_<id>` (per docs).

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/reddit_ads/README.md`
- The literal option values for `reporting_mode` (constants `STANDARD_MODE` / `CUSTOM_MODE`) and the stored shape of the `ad_accounts` multi-select were not resolved. Copy them from a UI-created sync.
