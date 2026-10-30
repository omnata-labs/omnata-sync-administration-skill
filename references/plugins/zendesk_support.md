# Zendesk Support

| | |
|---|---|
| Plugin FQN | `OMNATA__ZENDESK_SUPPORT` |
| Page | `zendesk_support.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Method**: `OAuth (User Created)`, authorization code. Fields: `subdomain`, `product_plan` (`free`, `team`, `professional` or `enterprise`, used for the rate-limit quota), and optional `high_volume_api_addon`.
- OAuth values for the SQL route:
  - Authorization endpoint: https://<subdomain>.zendesk.com/oauth/authorizations/new
  - Token endpoint: https://<subdomain>.zendesk.com/oauth/tokens
  - Scopes: `read`, `write`
- Only direct connectivity is supported.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `max_concurrent_queries_per_stream` (required, 1 to 10, default 5): maximum parallel queries for streams that download in parallel.

**Streams**: mostly static, e.g. `tickets`, `users`, `organizations`, plus dynamic custom object streams. Streams define no default cursor field, so incremental streams may need `STREAM_CURSOR_FIELDS`; this wasn't verified.

## Outbound

> **Warning: permanent deletion.** `Delete` deletes records in Zendesk, and `Mirror` removes records that are no longer in the source. Omnata can't restore them. Raise this when the user picks either strategy, before any other configuration. List what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation.

**Sync parameters** (`SYNC_PARAMETERS`):
- `zendesk_object`: the object to load into.
- `update_field` (Update, Upsert and Mirror only): the unique field used to match existing records.
- `skip_verify_email` (only when `zendesk_object` is `user`): skip email verification.

**Field mappings**: `field_mapping_selector`, based on `update_field` for match strategies, otherwise `zendesk_object`.


Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- API rate limits depend on the Zendesk plan. Check the docs before raising concurrency.
