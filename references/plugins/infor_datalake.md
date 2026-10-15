# Infor Datalake

| | |
|---|---|
| Plugin ID | `infor_datalake` |
| Plugin FQN | `MONITORIAL__INFOR_DATALAKE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/infor_data_lake/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `variations` (required): `AllVariations` (default) or `HighestVariation`. Which record variations to retrieve.
- `company_numbers` (optional, default `100`): comma-separated company numbers (CONO) to filter on, for example `100,200`.
- `min_acquisition_date` (optional): earliest date to load, format `yyyy-MM-dd`. Validated in code.
- `additional_where_clause` (optional): extra filter applied to all streams, for example `column_name = value`.
- `include_reconciliation_records` (optional, default false): include records found in the latest reconciliation at the end of the run.
- `include_reconciliation_delete_records` (optional, default false): include records no longer present in the source per the latest reconciliation.
- `table_category` (required, multi-select): stream categories to list. Options are built dynamically from Data Catalog table name prefixes.

**Streams**: dynamic, read from the Infor Data Catalog API and filtered by `table_category`. No streams are listed until a category is chosen. Stream names are the uppercased catalog object names (for example M3 tables such as `MITMAS`). Primary keys come from each object's `IdentifierPaths` (composite allowed). Default cursor is `lastModified` on every stream. Objects with no identifier paths would have no primary key and need `STREAM_PRIMARY_KEYS`.

**Sync strategies supported**: every stream supports `Incremental` and `Full Refresh`. Docs recommend `Incremental` to reduce Data Lake load.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'infor_datalake-inbound',
    SYNC_NAME          => 'Infor Datalake to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['MITMAS', 'OCUSMA'],
    SYNC_STRATEGY      => 'Incremental'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'variations', 'HighestVariation',
                            'company_numbers', '100',
                            'table_category', ARRAY_CONSTRUCT('<category>')),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Connection uses ION API credentials (the `.ionapi` file content). Only direct connectivity is supported.
- Per docs, `merge` storage enforces `HighestVariation` and keeps only the latest record version. `append` honours the chosen `variations` value.
- `table_category` must be set before streams can be listed, and its option keys depend on the tenant's catalog. Query the form options or copy from a UI-created sync.

## Sources

- Code: `omnata-labs/plugin-infor-data-lake` at `src/plugin.py`, `src/metadata/database_metadata.py`, `src/metadata/database_table_categories.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/infor_data_lake/README.md`
- `MITMAS` and `OCUSMA` appear in the plugin's static M3 table classification list. Their presence in a given tenant's catalog was not verified.
- The exact category key format (prefix values) depends on live API data and could not be verified. `<category>` is a placeholder.
- Manifest `docs_url` points to `apps/infor-datalake`, but the docs folder is `infor_data_lake`.
