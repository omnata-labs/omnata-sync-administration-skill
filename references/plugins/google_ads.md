# Google Ads

| | |
|---|---|
| Plugin ID | `google_ads` |
| Plugin FQN | `OMNATA__GOOGLE_ADS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Not supported |
| Docs | `apps/google_ads/README.md` |

## Connection

Follow `configure-connections.md`. One method, `OAuth` (`authorization_code`), scope `https://www.googleapis.com/auth/adwords`, token endpoint `https://oauth2.googleapis.com/token`. Field: `developer_token` (secret, optional). It is legacy: the plugin help text says Google sunset developer tokens on September 9, 2026 and API access now comes from the GCP project owning the OAuth client. Leave it blank; a saved token is still sent if present.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `customer_id` (required): dropdown populated dynamically from the Google Ads customers the connection can access.
- `reporting_mode` (required): `standard` (default) or `custom`. Changing it changes the stream list and the remaining fields.
- `backfill_days` (optional): days of history on the first sync of a metric report. Default `365`. Capped per report where Google limits it.
- Custom mode only: `resource` (required, the Google Ads resource to report on), `attribute_fields` (optional, comma-separated fully-qualified attribute fields such as `campaign.name`), `segments` (optional, comma-separated fully-qualified segments such as `segments.device`). `field_guidance` is a read-only information field, do not pass it.

**Streams**: depend on `reporting_mode`. Standard mode returns a static catalog, for example `campaign_performance`, `ad_group_performance`, `conversion_actions`, `labels`, `campaign_budgets`. Custom mode returns a single stream named `{resource}_report_daily`, built dynamically from `resource`, `attribute_fields` and `segments` (requires API calls to Google's field metadata). All streams have source-defined primary keys. Metric reports have a source-defined cursor (`segments.date`). Entity reports have no cursor. For reports with a Google lookback limit, a saved cursor older than that limit (for example 90 days for `click_performance`) is clamped forward to it, so data older than the limit is not re-requested after a long pause.

**Sync strategies supported**: metric reports support `Incremental` and `Full Refresh`. Entity reports are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'google_ads-inbound',
    SYNC_NAME          => 'Google Ads to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['campaign_performance', 'ad_group_performance', 'campaign_budgets'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'customer_id', '<customer_id>',
                            'reporting_mode', 'standard',
                            'backfill_days', '365'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

Outbound syncs are not supported for this plugin (the docs also say "Not yet supported"). Do not configure outbound syncs for it.

## Notes

- One customer per sync. Create one sync per customer on the same connection.
- `click_performance` (resource `click_view`) is fetched one day at a time due to a Google Ads API constraint, so large backfills on it are slow.
- In custom mode, set `resource`, `attribute_fields` and `segments` before listing streams, because the stream name and schema are derived from them. Incompatible segments fail at configuration time.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/google_ads/README.md`
- Docs describe a "Campaign Report Grouping" multi-select parameter for Standard mode. The plugin doesn't offer this parameter, so it's omitted here.
- Docs say 28 standard reports. Exact count not re-verified against code.
- Manifest `docs_url` is the generic `https://docs.omnata.com`.
