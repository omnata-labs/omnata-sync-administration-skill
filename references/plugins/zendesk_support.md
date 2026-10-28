# Zendesk Support

| | |
|---|---|
| Plugin ID | `zendesk_support` |
| Plugin FQN | `OMNATA__ZENDESK_SUPPORT` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/zendesk_support/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `max_concurrent_queries_per_stream` (required, slider 1 to 10, default 5): maximum parallel queries for streams that download in parallel.

**Streams**: mostly static, plus dynamic custom object streams. Representative: `tickets`, `ticket_events`, `ticket_metrics`, `users`, `organizations`, `groups`, `articles`. Dynamic: `custom_object_<key>` and `legacy_custom_object_<type>`. Static streams define primary key `id`. `ticket_fields` has `source_defined_cursor=False`. No `default_cursor_field` is set on streams in the list.

**Sync strategies supported**: most streams support `Incremental` and `Full Refresh`. `ticket_fields` and newer custom objects are `Full Refresh` only; legacy custom objects support Incremental via the events API.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'zendesk_support-inbound',
    SYNC_NAME          => 'Zendesk Support to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['tickets', 'users', 'organizations'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('max_concurrent_queries_per_stream', 5),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`): `Create`, `Upsert`, `Mirror`, `Update`, `Delete`.

**Sync parameters** (`SYNC_PARAMETERS`):
- `zendesk_object` (dynamic dropdown): object to load into.
- `update_field` (only for Update, Upsert, Mirror): unique field to match existing records.
- `skip_verify_email` (checkbox, only when `zendesk_object` is `user`): skip email verification.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, dynamic on `update_field` (match strategies) or `zendesk_object`.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- API rate limits depend on the Zendesk plan; see docs before raising concurrency.
- Supports inbound record filtering (Sync Engine custom record filtering via a user-defined function, added in engine V6.40).
- Only direct connectivity is supported.
- Connection method: "OAuth (User Created)" (authorization code; fields `subdomain`, `product_plan` (`free`, `team`, `professional`, `enterprise`; used for rate-limit quota), optional `high_volume_api_addon`). OAuth template endpoints are `https://<Zendesk subdomain>.zendesk.com/oauth/authorizations/new` and `https://<Zendesk subdomain>.zendesk.com/oauth/tokens`, scopes `read`, `write`.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/zendesk_support/README.md`
- Not verified: whether `zendesk_object` and `update_field` are required. The effect of `max_concurrent_queries_per_stream` could not be confirmed. How inbound record filtering is configured (UDF signature, sync parameter) is not verified. Cursor fields are not declared, so incremental streams may need `STREAM_CURSOR_FIELDS` or rely on plugin-internal state; not verified.
