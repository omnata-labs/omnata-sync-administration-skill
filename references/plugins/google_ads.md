# Google Ads

| | |
|---|---|
| Plugin FQN | `OMNATA__GOOGLE_ADS` |
| Page | `google_ads.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `OAuth` only. Field `developer_token` (secret, optional) is legacy. Google sunset developer tokens on September 9, 2026, and API access now comes from the GCP project that owns the OAuth client. Leave it blank. A saved token is still sent if present.
- **OAuth values**: grant type `authorization_code`; token endpoint `https://oauth2.googleapis.com/token`; scope `https://www.googleapis.com/auth/adwords`.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `customer_id` (required): from a dynamic list of Google Ads customers the connection can access.
- `reporting_mode` (required): `standard` (default) or `custom`. Changing it changes the stream list and the other fields.
- `backfill_days` (optional, default `365`): days of history on the first sync of a metric report. Capped per report where Google limits it.
- Custom mode only: `resource` (required, the Google Ads resource to report on), `attribute_fields` (optional, comma-separated fully-qualified fields such as `campaign.name`), `segments` (optional, comma-separated, such as `segments.device`).
- `field_guidance` is read-only. Don't pass it.

**Streams**: standard mode has a static catalog, for example `campaign_performance` and `ad_group_performance`. Custom mode returns one stream named after the resource with a _report_daily suffix, built from `resource`, `attribute_fields` and `segments`. For reports with a Google lookback limit, a saved cursor older than the limit (for example 90 days for `click_performance`) is moved forward to it, so older data isn't re-requested after a long pause.

## Notes

- Outbound isn't supported. Don't configure outbound syncs.
- One customer per sync. Create one sync per customer on the same connection.
- `click_performance` is fetched one day at a time because of a Google Ads API limit, so large backfills on it are slow.
- In custom mode, set `resource`, `attribute_fields` and `segments` before listing streams. Incompatible segments fail at configuration time.
