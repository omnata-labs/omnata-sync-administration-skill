# Reddit Ads

| | |
|---|---|
| Plugin FQN | `OMNATA__REDDIT_ADS` |
| Page | `reddit_ads.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required, multi-select): the Ad Accounts to sync. Options come from Reddit.
- `reporting_mode` (required): Standard (default) or Custom. Changes the stream list.
- `time_zone_id` (optional): time zone for daily report aggregation. Blank means UTC.
- `backfill_days` (optional): days of history on the first sync of a performance report (default 90, max 730).
- `restatement_days` (optional): trailing days re-read on each later run (default 30).
- `custom_breakdowns` and `custom_fields` (required in Custom mode): the breakdowns and columns for the custom report.

**Streams**: Standard mode has a fixed list of entity, metric and conversion streams (e.g. `campaigns`, `campaign_performance`). Custom mode produces one stream from the chosen breakdowns and fields, and lists nothing until both are set.

## Notes

- One Custom report per sync. Multiple custom reports need multiple syncs.
- Ad Account IDs look like a2_ followed by the ID.
- The literal values for `reporting_mode` and the stored shape of `ad_accounts` are unconfirmed. Copy them from a UI-created sync.
