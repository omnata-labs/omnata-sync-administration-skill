# Microsoft Ads

| | |
|---|---|
| Plugin ID | `microsoft_ads` |
| Plugin FQN | `OMNATA__MICROSOFT_ADS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/microsoft_ads/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `account_ids` (required, multi-select): Microsoft Advertising account IDs to sync.
- `reporting_timezone` (required): timezone for metric reports, from a static list.
- `backfill_days` (optional, default `365`): days of history loaded on the first sync of a metric report.

**Streams**: Static catalog. Entity streams `accounts`, `campaigns`, `ad_groups`, `ads` (primary key `Id`; `ad_groups` depends on `campaigns`, `ads` on `ad_groups`). Metric report streams such as `account_performance`, `campaign_performance`, `ad_group_performance`, `keyword_performance`, `search_query_performance`. All streams have a source-defined primary key and `source_defined_cursor` true.

**Sync strategies supported**: Entity streams are `Full Refresh` only. Metric report streams support `Full Refresh` and `Incremental` (on the report time period).

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'microsoft_ads-inbound',
    SYNC_NAME          => 'Microsoft Ads to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['campaigns', 'ad_groups', 'campaign_performance', 'keyword_performance'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('account_ids', ARRAY_CONSTRUCT('<account_id>'), 'reporting_timezone', '<timezone>', 'backfill_days', '365'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Repo is named `bing-ads` but the plugin ID is `microsoft_ads`.
- `account_ids` values are the numeric account IDs as strings; `reporting_timezone` must match a key in the plugin's timezone list.

## Sources

- Code: `omnata-labs/plugin-bing-ads` at `src/plugin.py`, `src/standard_reporting.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/microsoft_ads/README.md`
- Default cursor field name for metric reports not explicitly set in stream definitions; valid `reporting_timezone` values not listed here.
