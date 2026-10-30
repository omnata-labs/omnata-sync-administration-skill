# Meta Marketing

| | |
|---|---|
| Plugin FQN | `OMNATA__META_MARKETING` |
| Page | `meta_marketing.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required): the Meta ad accounts to sync.
- `reporting_mode` (required, default `standard`): `standard` uses a fixed report catalog; `custom` builds one user-defined report.
- `backfill_days` (optional): the initial backfill window in days.
- Custom mode only: `custom_level` (required, default `ad`), `custom_breakdowns` (required, a breakdown combo), `custom_metrics` (required, comma-separated fields), `custom_attribution_windows` (optional).

**Streams**: depend on `reporting_mode`. Standard mode has a fixed list of metric and entity streams, such as `campaign_performance` and `campaigns`. Custom mode gives exactly one stream, named from the level and breakdowns. Nothing is listed until `custom_metrics` is set. Primary keys and cursors are source-defined.

## Notes

- One sync holds one custom report. Several custom reports need several syncs.
- Changing `custom_level` or `custom_breakdowns` changes the stream name and grain, which creates a new destination table.
- The connection uses the read-only ads_read scope.
