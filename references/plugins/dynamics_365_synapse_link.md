# Microsoft Dynamics 365 Synapse Link

| | |
|---|---|
| Plugin FQN | `MONITORIAL__DYNAMICS_365_SYNAPSE_LINK` |
| Page | `dynamics_365_synapse_link.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Before you start**: Synapse Link must use "Enable incremental update folder structure", or the plugin can't read the export. The user also needs an Azure service principal with Storage Blob Data Reader on the storage account. See the docs.
- **Storage integration**: the connection needs a Snowflake storage integration (`azure_storage_integration`) granted to both `OMNATA_SYNC_ENGINE` and the plugin application.
- **Optional fields**: `d365_environment_url` (F&O) and `d365_crm_environment_url` (CRM/Dataverse) are only needed for reconciliations.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `include_metadata` (optional, default `true`): appends Synapse Link metadata (SinkCreatedOn, SinkModifiedOn) so every record version is kept. When `false`, only one record per `recid` and `recversion` is kept.

**Streams**: dynamic, one per entity in the Synapse Link export (e.g. `account`). Each stream supports exactly one strategy, so use `Auto` for a mixed selection.

## Notes

- Reconciliations are managed in the plugin's Streamlit app, not through sync parameters. It needs the `omnata_management` or `dynamics_reconciliation_management` application role.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
