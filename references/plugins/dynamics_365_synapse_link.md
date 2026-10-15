# Microsoft Dynamics 365 Synapse Link

| | |
|---|---|
| Plugin ID | `dynamics_365_synapse_link` |
| Plugin FQN | `MONITORIAL__DYNAMICS_365_SYNAPSE_LINK` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/dynamics_365_synapse_link/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `include_metadata` (optional checkbox, default `true`): appends Synapse Link metadata (SinkCreatedOn, SinkModifiedOn) so every record version from the data lake is kept. When `false`, only one record per `recid` and `recversion` combination is retained.

**Streams**: Dynamic. One stream per entity found in the Synapse Link export metadata on the connection's ADLS Gen2 container (read through the plugin's internal stage). Stream names are the exported entity (table) names, for example `account` or `generaljournalentry`. Primary keys come from key columns in the entity schema. No stream declares a default cursor field; cursors are source-defined (folder timestamps and record versions).

**Sync strategies supported**: Each stream supports exactly one strategy. Most entities are `Incremental` only. A fixed list of small kernel/system tables (for example `dataarea`, `userinfo`, `securityrole`, `sqldictionary`, `partitions`) and the option set metadata entities are `Full Refresh` only. `SYNC_STRATEGY => 'Auto'` is the safest choice for a mixed selection.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'dynamics_365_synapse_link-inbound',
    SYNC_NAME          => 'Microsoft Dynamics 365 Synapse Link to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['account', 'generaljournalentry', 'dataarea'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('include_metadata', true),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Synapse Link must be configured with "Enable incremental update folder structure", otherwise the plugin cannot read the export.
- The connection requires a Snowflake storage integration (`azure_storage_integration`) granted to both `OMNATA_SYNC_ENGINE` and the plugin application, plus an Azure service principal with Storage Blob Data Reader on the storage account.
- Tuning parameter (not a sync parameter): `max_concurrent_folders` (1 to 50) controls how many date folders are processed concurrently.
- `d365_environment_url` / `d365_crm_environment_url` on the connection are only needed for the reconciliation feature described in the docs.

## Sources

- Code: `plugin-dynamics-365-synapse-link` at `src/plugin.py`, `src/metadata/model_metadata.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/dynamics_365_synapse_link/README.md`
- Stream names depend on which tables are exported. `account` is taken from a docs file path example and `generaljournalentry` from the docs reconciliation example; neither is guaranteed to exist in a given environment. The default for `max_concurrent_folders` was not checked.
