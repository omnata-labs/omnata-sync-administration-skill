# Shopify

| | |
|---|---|
| Plugin FQN | `OMNATA__SHOPIFY` |
| Page | `shopify.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `force_customer_pii_field` (required, default `pii_fields_follow_account_plan`): controls whether the customer streams request PII fields. Shopify always decides whether PII is released, based on the store's plan and the app's access scopes; no setting overrides that.
  - `pii_fields_follow_account_plan` (default): follows the connection's User Tier field, which the user sets; it isn't detected from Shopify. With Basic, PII fields aren't requested. With any other tier, they are, so a wrong tier behaves like force fetch.
  - `pii_fields_force_fetch`: always requests the PII fields, even when the user doesn't know what their plan allows. Shopify then either returns the refused fields as null, or rejects the request with an access-denied error, which fails the whole stream so its non-PII data doesn't sync either.
  - `pii_fields_force_reject`: never requests PII fields. The customer streams sync their non-PII fields only.

  > **Warning: personal data.** Any PII Shopify releases (names, emails, addresses, phone numbers) is copied into Snowflake. Tell the user, and confirm they're allowed to copy it, before choosing a value other than `pii_fields_force_reject`. If a customer stream fails with access denied, suggest `pii_fields_force_reject` or checking the app's scopes.

**Streams**: a fixed list (e.g. `customers`, `orders`). Several order child streams depend on `orders`.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `shopify_object`: the target object (`customers`, `products`, `orders` or `inventory_item_levels`).
- `quantity_name` (required only for `inventory_item_levels`): `available` or `on_hand`.

**Field mappings**: `field_mapping_selector`. Target fields depend on `shopify_object`, or `quantity_name` for inventory levels.

> **Warning: permanent deletion.** `Delete` permanently deletes records in Shopify. Omnata can't restore them. List what will be deleted and wait for the user's explicit yes; don't treat an unclear reply as confirmation.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- `apply_outbound_target_type` exists for backward compatibility with syncs created before target types.
- Both connection methods (`API Access Token` and `Client Credentials (Client ID/Secret)`) have a required User Tier field: Basic, Shopify, Advanced, Shopify Plus or Enterprise. Ask the user for their real Shopify plan. It sets the API rate limits, and under the default PII setting it decides whether PII is requested.
