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

## Notes

- Stream names are camelCase API collection names (e.g. `bounceLogs`), so match the case exactly.
- The available stream list depends on the ActiveCampaign plan behind the API key.
