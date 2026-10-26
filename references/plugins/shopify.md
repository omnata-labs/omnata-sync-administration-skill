# Shopify

| | |
|---|---|
| Plugin ID | `shopify` |
| Plugin FQN | `OMNATA__SHOPIFY` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/shopify/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `force_customer_pii_field` (required, dropdown, default `pii_fields_follow_account_plan`): controls fetching customer PII fields. Values: `pii_fields_force_fetch`, `pii_fields_force_reject`, `pii_fields_follow_account_plan`.

**Streams**: static list of 20 streams. Representative: `customers`, `products`, `orders`, `product_variants`, `inventory_levels`, `locations`, `payouts`, `analytics_daily`. Several child streams (`order_returns`, `order_shipping_lines`, `order_fulfillments`, etc.) depend on `orders`. All streams checked define `source_defined_primary_key` and `source_defined_cursor=True`.

**Sync strategies supported**: core objects (`customers`, `products`, `orders`) support `Incremental` and `Full Refresh`. Order child streams are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'shopify-inbound',
    SYNC_NAME          => 'Shopify to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['customers', 'products', 'orders'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('force_customer_pii_field', 'pii_fields_follow_account_plan'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): `Shopify Objects`, supporting Create, Upsert, Update, Delete. Its target parameter is `shopify_object`.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: creates new records.
- `Upsert`: creates or updates records.
- `Update`: updates existing records.
- `Delete`: deletes records.

**Sync parameters** (`SYNC_PARAMETERS`):
- `shopify_object` (dropdown): `customers`, `products`, `orders`, `inventory_item_levels`.
- `quantity_name` (required, only when `shopify_object` is `inventory_item_levels`): `available` or `on_hand`.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`. Target fields are dynamic, depending on `shopify_object` (or `quantity_name` for inventory levels).

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- `apply_outbound_target_type` exists for backward compatibility with syncs created before target types.
- Customer PII access depends on the Shopify plan and app scopes; see docs.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/shopify/README.md`
- Not verified: whether `shopify_object` is required. Cursor fields for each stream were not individually checked.
