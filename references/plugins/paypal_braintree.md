# PayPal Braintree

| | |
|---|---|
| Plugin ID | `paypal_braintree` |
| Plugin FQN | `OMNATA_LABS__PAYPAL_BRAINTREE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/paypal_braintree/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`. `rest_fetch_workers` and `enqueue_batch_size` are optional tuning parameters, not sync parameters.

**Streams**: Static list of four: `transactions`, `subscriptions`, `disputes`, `customers`. All have primary key `id` and a source-defined cursor (`created_at`, except `disputes` which uses `received_date`).

**Sync strategies supported**: All streams support `Incremental` and `Full Refresh`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'paypal_braintree-inbound',
    SYNC_NAME          => 'PayPal Braintree to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['transactions', 'subscriptions', 'disputes', 'customers'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Incremental cursors are creation timestamps, so status changes on existing records are not picked up incrementally. Docs recommend a periodic Full Refresh sync alongside the incremental one.
- `disputes` cursor is day precision, so each incremental run re-reads the current day.
- Defaults are memory-conservative (1 worker, 500 records per upload). Raise tuning parameters for large merchants.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/paypal_braintree/README.md`
- Conflict: docs name the `disputes` cursor `receivedDate`; code sets `default_cursor_field="received_date"`. Code used here.
