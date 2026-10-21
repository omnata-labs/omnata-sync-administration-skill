# LinkedIn Ads

| | |
|---|---|
| Plugin ID | `linkedin_ads` |
| Plugin FQN | `OMNATA__LINKEDIN_ADS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/linkedin_ads/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required, multi-select): the LinkedIn ad account IDs to sync. Options come from the `/adAccounts` search finder. The plugin splits the value on commas, so pass a comma-separated string of account IDs.

**Streams**: static list built in code. `accounts` and `campaigns`, plus one `ad_analytics_by_<pivot>_daily` stream per analytics pivot (for example `ad_analytics_by_campaign_daily`, `ad_analytics_by_creative_daily`, `ad_analytics_by_member_country_daily`). Only daily granularity is enabled; weekly and monthly are commented out. Every stream defines `id` as its primary key and uses a source-defined cursor, so `STREAM_PRIMARY_KEYS` / `STREAM_CURSOR_FIELDS` are not needed.

**Sync strategies supported**: `accounts` and `campaigns` are Full Refresh only. All `ad_analytics_by_*` streams are Incremental only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'linkedin_ads-inbound',
    SYNC_NAME          => 'LinkedIn Ads to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['accounts', 'campaigns', 'ad_analytics_by_campaign_daily'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('ad_accounts', '<ad_account_id>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Because stream strategies are fixed per stream, `'Auto'` is the safest `SYNC_STRATEGY` when mixing entity and analytics streams.
- The code contains an `outbound_configuration_form` and a "Publish Conversion Events" action, but the strategy is commented out of the manifest pending LinkedIn developer token approval. Outbound syncs cannot be configured.

## Sources

- Code: `omnata-labs/plugin-linkedin-ads` branch `main-v1` (latest commit 2026-10-08) at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/linkedin_ads/README.md` (agrees: no outbound, offline conversions "coming soon").
- Not verified: the exact JSON format the UI stores for the multi-select `ad_accounts` value; the comma-separated string is inferred from `sync_inbound` splitting on commas.
