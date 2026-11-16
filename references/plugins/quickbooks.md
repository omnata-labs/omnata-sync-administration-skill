# QuickBooks Online

| | |
|---|---|
| Plugin FQN | `OMNATA__QUICKBOOKS` |
| Page | `quickbooks.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

## Connection

Follow `configure-connections.md`. Record only:
- **Methods**: OAuth, with `environment` (`production` by default, or `sandbox` for Intuit developer sandbox companies) and `realm_id` (the Company ID). OAuth uses the user's own Intuit app, so the user completes it in the Omnata UI.
- **Before you start**: the user needs an Intuit developer app and the company's Company ID (QuickBooks Settings > Account and settings > Billing & subscription). See the docs.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: static list of QuickBooks entities (lists and transactions). Primary key is `Id`.

## Notes

- One connection reads one company. Use a connection per company.
- Deletes are picked up only if the stream runs at least every 30 days. After a longer gap, run a Full Refresh to reconcile deletes.
