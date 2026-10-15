# Salesforce Marketing Cloud

| | |
|---|---|
| Plugin ID | `sfmc` |
| Plugin FQN | `OMNATA__SFMC` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/sfmc/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `stream_type` (required): `data_extension`, `journey_history`, or `tracking_extract` (SFTP connection methods only). Changes the stream list and other fields.
- `activity_types`, `statuses` (required for `journey_history`, multi-select).
- `data_extension_filter` (`filter` or `all`) and `data_extension_filter_text` (required when `filter`): limit listed Data Extensions.
- `account_id` (optional, data_extension): override the connection's Account ID.
- `use_ftp_for_export` (SFTP methods) and `auto_fix_csv` (optional, data_extension).

**Streams**: Dynamic for `data_extension` (one per Data Extension, named by its Name) and `journey_history` (one per journey, named by journey name, key `ActivityId`). Static for `tracking_extract` (for example `Bounces`, `Clicks`, `Conversions`). Data Extensions with no primary key fields have no source-defined primary key. No Data Extension has a default cursor.

**Sync strategies supported**: Data Extensions: `Full Refresh`, plus `Incremental` when exactly one primary key field exists. Journey history and tracking extract: `Incremental` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'sfmc-inbound',
    SYNC_NAME          => 'Salesforce Marketing Cloud to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<data_extension_name>'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('stream_type', 'data_extension', 'data_extension_filter', 'all'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): `Data Extension`: Create, Upsert, Replace, Mirror.

**Strategies** (`SYNC_STRATEGY_NAME`): `Create` (AddAndDoNotUpdate), `Upsert` (AddAndUpdate), `Replace` (Overwrite), `Mirror` (AddAndUpdate, or ColumnBased when deletes exist).

**Sync parameters** (`SYNC_PARAMETERS`):
- `data_extension_name` (required): target Data Extension (option carries metadata such as ObjectID and Name).
- `create_if_missing` (optional, default false): create the Data Extension if absent.
- `account_id` (optional): override the connection's Account ID.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`. Targets are the columns of the chosen Data Extension, fetched dynamically; new columns can be created. A primary key is required even for Replace.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Outbound requires an SFTP or Cloud Storage connection method; API-only connections show an error field instead.
- Tracking extract streams are only offered on SFTP connection methods.

## Sources

- Code: `omnata-labs/plugin-sfmc` at `src/plugin.py`, `src/plugin_inbound_functionality.py`, `src/plugin_outbound_functionality.py`, `src/sfmc_helpers/journeys.py`, `src/sfmc_helpers/schemas.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/sfmc/README.md`
- Conflict: docs say Data Extensions are Full Refresh only; code also allows Incremental for single-PK Data Extensions. Code used here. Docs do not mention tracking extract streams.
- `data_extension_name` stores option metadata, so hand-built values are risky. Not verified how to construct it outside the UI.
