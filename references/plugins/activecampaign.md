# ActiveCampaign

| | |
|---|---|
| Plugin ID | `activecampaign` |
| Plugin FQN | `OMNATA__ACTIVECAMPAIGN` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/activecampaign/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: A fixed list of 14 collections (for example `contacts`, `accounts`, `campaigns`, `lists`, `tags`, `automations`). At listing time each collection is probed, and streams the account's plan does not include (HTTP 403 with a detail message) are silently omitted. All streams have source-defined primary key `id`.

**Sync strategies supported**: Only `contacts` supports `Incremental` (cursor `udate`). Every other stream is `Full Refresh` only and has no default cursor.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'activecampaign-inbound',
    SYNC_NAME          => 'ActiveCampaign to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['contacts', 'accounts', 'campaigns', 'lists'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Stream names are camelCase API collection names (`bounceLogs`, `contactTags`), so match the case exactly.
- The available stream list depends on the ActiveCampaign plan behind the API key.
- Connection method: "API Key" with `account_url` (the API URL, e.g. `https://<account>.api-us1.com`) and `api_token` (secret). Both are on Settings > Developer in ActiveCampaign; each user has their own key.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/activecampaign/README.md`
- FQN derived from developer_id and plugin_id, not confirmed against a live connection.
