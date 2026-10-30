# Microsoft Dynamics 365 Business Central

| | |
|---|---|
| Plugin FQN | `MONITORIAL__DYNAMICS_365_BUSINESS_CENTRAL` |
| Page | `dynamics_365_business_central.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- Access tokens last 60 minutes. Long-running syncs should use a connection on the "OAuth (Plugin managed tokens)" method.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `companies` (required, multi-select): the Business Central company IDs to retrieve data for. Values are GUIDs, not display names.
- `api_set` (required, default `api`): which API set to read. `api` is the v2.0 API, `ODataV4` is OData, and `custom` uses the custom API publisher, group and version from the connection.

**Streams**: dynamic, built from the metadata of the selected `api_set`. Changing `api_set` changes the stream list entirely. Generated child streams (line items) depend on their parent stream.

## Notes

- Look up company IDs from an existing UI-created sync or the Business Central companies API.
- For large initial loads, the docs recommend splitting objects across several syncs.
- Use `Full Refresh` for entities where deletes matter (for example accounts, currencies, employees). Deletes aren't captured incrementally.
- Unsupported endpoints: timeRegistrationEntries, subscriptions, picture, documentAttachment, pdfDocument.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
