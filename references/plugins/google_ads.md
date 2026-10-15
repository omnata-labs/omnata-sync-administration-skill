# Google Ads

| | |
|---|---|
| Plugin ID | `google_ads` |
| Plugin FQN | `OMNATA__GOOGLE_ADS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Declared in manifest but not implemented (see Outbound) |
| Docs | `apps/google_ads/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `customer_id` (required): dropdown populated dynamically from the Google Ads customers the connection can access.
- `reporting_mode` (required): `standard` (default) or `custom`. Changing it changes the stream list and the remaining fields.
- `backfill_days` (optional): days of history on the first sync of a metric report. Default `365`. Capped per report where Google limits it.
- Custom mode only: `resource` (required, the Google Ads resource to report on), `attribute_fields` (optional, comma-separated fully-qualified attribute fields such as `campaign.name`), `segments` (optional, comma-separated fully-qualified segments such as `segments.device`). `field_guidance` is a read-only information field, do not pass it.

**Streams**: depend on `reporting_mode`. Standard mode returns a static catalog defined in `standard_reporting.py`, for example `campaign_performance`, `ad_group_performance`, `conversion_actions`, `labels`, `campaign_budgets`. Custom mode returns a single stream named `{resource}_report_daily`, built dynamically from `resource`, `attribute_fields` and `segments` (requires API calls to Google's field metadata). All streams have source-defined primary keys. Metric reports have a source-defined cursor (`segments.date`). Entity reports have no cursor.

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

The manifest lists `Create` and `Upsert`, but `outbound_configuration_form` and `sync_outbound` are empty stubs (`pass`), and the docs state outbound is "Not yet supported". Do not configure outbound syncs for this plugin. No target types are defined.

## Notes

- One customer per sync. Create one sync per customer on the same connection.
- `click_view` is fetched one day at a time due to a Google Ads API constraint, so large backfills on it are slow.
- In custom mode, set `resource`, `attribute_fields` and `segments` before listing streams, because the stream name and schema are derived from them. Incompatible segments fail at configuration time.

## Sources

- Code: `omnata-labs/plugin-google-ads` at `src/plugin.py`, `src/standard_reporting.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/google_ads/README.md`
- Docs describe a "Campaign Report Grouping" multi-select parameter for Standard mode. No such field exists in `inbound_configuration_form`, so it is omitted here. Its parameter name could not be verified.
- Docs say 28 standard reports. Exact count not re-verified against code.
- Manifest `docs_url` is the generic `https://docs.omnata.com`.
