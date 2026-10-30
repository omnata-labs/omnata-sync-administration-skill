# PayPal Braintree

| | |
|---|---|
| Plugin FQN | `OMNATA_LABS__PAYPAL_BRAINTREE` |
| Page | `paypal_braintree.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: a fixed list (e.g. `transactions`, `disputes`).

## Notes

- Incremental cursors are creation timestamps, so status changes on existing records aren't picked up incrementally. The docs recommend a periodic Full Refresh sync alongside the incremental one.
- The `disputes` cursor has day precision, so each incremental run re-reads the current day.
- Defaults are memory-conservative. Large merchants may need higher tuning values.
