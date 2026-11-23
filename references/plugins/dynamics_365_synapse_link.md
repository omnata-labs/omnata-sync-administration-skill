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
- To investigate "Failed to process folder", slow catch-up or a sync that loads no rows, call the plugin's `diagnostics` objects: procedures `d365_stream_status(sync, stream, run_deadline_minutes)`, `d365_diagnose_stream(sync_slug, stream_name, folder, from_folder, to_folder)` and `d365_folder_counts(connection_slug, stream_name, folder, ...)`, and table functions `d365_sync_progress(sync, stream, latest_run_only)` and `d365_staging_batches(sync, stream, status)`. Only the first argument is required; pass skipped arguments as typed nulls (`null::varchar`). A sync's slug is recognised only after its first run; before that use its `SYNC_ID`. The caller needs the plugin's `consumer_function_caller` application role, and the plugin application needs `OMNATA_SYNC_ENGINE`'s `views_only` application role.
- A large backlog can take several runs. Staged data and the saved position are only sent when the last folder is done, so a stream can show no new rows until then.
- **Before running** `d365_discard_staging_batch(staging_batch_id)`: it throws away an open staging batch and everything it staged. Nothing is sent to the destination and the next run reprocesses those folders from the saved position. Show the user the batch (from `d365_staging_batches`) and its stream. Confirm with the user before using it.
- Scheduled reconciliation jobs created before V3.4 keep their old task timeout until they are re-saved in the plugin's Streamlit app.
