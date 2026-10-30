# Infor Datalake

| | |
|---|---|
| Plugin FQN | `MONITORIAL__INFOR_DATALAKE` |
| Page | `infor_datalake.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`. Uses ION API credentials (the .ionapi file content). Only direct connectivity is supported.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `variations` (required): `AllVariations` (default) or `HighestVariation`. Which record variations to retrieve.
- `company_numbers` (optional, default `100`): comma-separated company numbers (CONO), for example 100,200.
- `min_acquisition_date` (optional): earliest date to load, format yyyy-MM-dd. Other formats are rejected.
- `additional_where_clause` (optional): extra filter for all streams, for example column_name = value.
- `include_reconciliation_records` (optional, default false): include records found in the latest reconciliation at the end of the run.
- `include_reconciliation_delete_records` (optional, default false): include records no longer in the source per the latest reconciliation.
- `table_category` (required, multi-select): stream categories to list. Options come from Data Catalog table name prefixes.

**Streams**: dynamic, from the Infor Data Catalog, filtered by `table_category`. Nothing is listed until a category is set. Names are uppercased catalog object names (for example `MITMAS`). Objects with no identifier paths have no primary key and need `STREAM_PRIMARY_KEYS`.

## Notes

- `merge` storage enforces `HighestVariation` and keeps only the latest record version. `append` honours the chosen `variations`.
- `table_category` option keys depend on the tenant's catalog. Query the form options or copy from a UI-created sync.
