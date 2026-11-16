# Pipedrive

| | |
|---|---|
| Plugin FQN | `OMNATA__PIPEDRIVE` |
| Page | `pipedrive.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

## Connection

Follow `configure-connections.md`. Record only:
- **Methods**: API Token, with the secret field `api_token`.
- **Before you start**: the token belongs to one Pipedrive user and the user must be active. The sync sees what that user can see.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: static. Custom fields are discovered per account and added to the stream schemas. On deals, persons, organizations, products and activities they are nested under `custom_fields`, keyed by Pipedrive's 40 character field key, not the field name.

## Notes

- Deleted records are not detected. Use Full Refresh to drop records deleted in Pipedrive.
- Pipedrive's daily API budget is shared across the whole company, so large syncs can slow other Pipedrive integrations.
