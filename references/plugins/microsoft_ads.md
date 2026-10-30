# Microsoft Ads

| | |
|---|---|
| Plugin FQN | `OMNATA__MICROSOFT_ADS` |
| Page | `microsoft_ads.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `account_ids` (required, multi-select): the Microsoft Advertising account IDs to sync, as numeric IDs in string form.
- `reporting_timezone` (required): the timezone for metric reports. It must match a value from the plugin's timezone list.
- `backfill_days` (optional, default `365`): days of history loaded on the first sync of a metric report.

**Streams**: static. There are entity streams, such as `campaigns`, and metric report streams, such as `campaign_performance`. Some entity streams depend on others: `ad_groups` needs `campaigns`, and `ads` needs `ad_groups`. Primary keys and cursors are source-defined.

## Notes

- The source repo is named bing-ads, but the plugin ID is `microsoft_ads`.
