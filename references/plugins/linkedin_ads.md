# LinkedIn Ads

| | |
|---|---|
| Plugin FQN | `OMNATA__LINKEDIN_ADS` |
| Page | `linkedin_ads.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required, multi-select): the LinkedIn ad account IDs to sync. The plugin splits the value on commas, so pass a comma-separated string of IDs. The exact format the UI stores wasn't verified.

**Streams**: static, for example `accounts`, `campaigns` and `ad_analytics_by_campaign_daily`. Only daily analytics granularity is available.

## Notes

- Stream strategies are fixed per stream, so `Auto` is the safest `SYNC_STRATEGY` when mixing entity and analytics streams.
- Outbound (Publish Conversion Events) isn't available yet, pending LinkedIn developer token approval. Don't configure outbound syncs.
