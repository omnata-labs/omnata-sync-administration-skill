# Stripe

| | |
|---|---|
| Plugin FQN | `OMNATA__STRIPE` |
| Page | `stripe.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: API Key, with the secret field `secret_key`.
- **Before you start**: a Stripe restricted key with Read access to Balance and to every object to be synced is preferred over a full secret key. A test mode key syncs test data only.
- **Quirks**: the connection test reads the account balance, so a restricted key without Read on Balance fails the test even if it can read the synced objects. Keys start with `rk_` (restricted) or `sk_` (secret), which helps redact output.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.
- `enqueue_batch_size` (tuning, optional, default `500`): records buffered before each upload. Lower it if the sync runs out of memory.

**Streams**: a static list, one per Stripe object. Nested objects and lists land as VARIANT columns. Expandable references such as `customer` hold only the ID.

## Notes

- Incremental picks up newly created objects only, because the cursor is `created`. Changes to existing objects (subscription status, invoice paid, refunds on older charges) are missed. Use Full Refresh for streams whose records change.
- Stripe Connect is not supported: one connection syncs one Stripe account.
