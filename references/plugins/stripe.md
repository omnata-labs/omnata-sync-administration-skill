# Stripe

| | |
|---|---|
| Plugin FQN | `OMNATA__STRIPE` |
| Page | `stripe.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

## Connection

Follow `configure-connections.md`. Record only:
- **Methods**: API Key, with the secret field `secret_key`.
- **Before you start**: the key needs Read access to Balance as well as the synced objects, or the connection test fails. See the docs.
- **Quirks**: keys start with `rk_` or `sk_`, which helps redact output.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: static. Incremental only picks up newly created objects, so changes to existing records (subscription status, invoice paid) are missed. Use Full Refresh for streams whose records change.

## Notes

- One connection syncs one Stripe account. Stripe Connect accounts are not supported.
