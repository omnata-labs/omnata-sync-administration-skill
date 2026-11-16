# ActiveCampaign

| | |
|---|---|
| Plugin FQN | `OMNATA__ACTIVECAMPAIGN` |
| Page | `activecampaign.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- **Methods**: API Key, with `account_url` (the API URL, e.g. `https://<account>.api-us1.com`) and `api_token` (secret). Both are on Settings > Developer in ActiveCampaign. Each user has their own key.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: a fixed list of collections (e.g. `contacts`, `accounts`). Streams the account's plan doesn't include are silently left out.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`): None. Contacts is the only target.

**Field mappings**: `field_mapping_selector`, with standard and custom contact fields. Create and Upsert need `email` mapped. Update and Delete match a contact by the ID the sync recorded, a mapped `id` (Contact ID, match only), or `email`.

**Before running**: `Delete` permanently deletes contacts in ActiveCampaign. Show the user which contacts will be affected. Confirm with the user before using it.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Stream names are camelCase API collection names (e.g. `bounceLogs`), so match the case exactly.
- The available stream list depends on the ActiveCampaign plan behind the API key.
