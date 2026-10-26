# Meta Marketing

| | |
|---|---|
| Plugin ID | `meta_marketing` |
| Plugin FQN | `OMNATA__META_MARKETING` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/meta_marketing/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `ad_accounts` (required): the Meta ad accounts to sync.
- `reporting_mode` (required, default `standard`): `standard` (fixed report catalog) or `custom` (one user-defined report).
- `backfill_days` (optional): initial backfill window in days.
- Custom mode only: `custom_level` (required, default `ad`), `custom_breakdowns` (required, a breakdown combo slug), `custom_metrics` (required, comma-separated fields), `custom_attribution_windows` (optional).

**Streams**: depend on `reporting_mode`, and are computed offline (no API call). Standard mode is a fixed catalog of metric streams such as `account_performance`, `campaign_performance`, `ad_set_performance`, `ad_performance`, `demographic_performance`, `country_performance`, and entity streams such as `ad_accounts`, `campaigns`, `ad_sets`, `ads`, `ad_creatives`, `custom_conversions`. Custom mode produces exactly one stream whose name is built from the level and breakdown combo, and nothing is listed until `custom_metrics` is set. All streams have a source-defined primary key (possibly composite) and a source-defined cursor.

**Sync strategies supported**: every stream supports Incremental and Full Refresh.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'meta_marketing-inbound',
    SYNC_NAME          => 'Meta Marketing to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['campaign_performance', 'ad_performance', 'campaigns'],
    SYNC_STRATEGY      => 'Incremental'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('ad_accounts', '<ad_account_id>', 'reporting_mode', 'standard'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- One sync holds one Custom report. Several custom reports require several syncs.
- Changing `custom_level` or `custom_breakdowns` changes the stream name (and primary key grain), creating a new destination table.
- Inbound only: the connection uses the read-only `ads_read` scope.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/meta_marketing/README.md` (agrees: inbound only, all streams support both strategies).
- Not verified: the stored value format for multi-value `ad_accounts`, and the full list of `custom_breakdowns` slugs.
