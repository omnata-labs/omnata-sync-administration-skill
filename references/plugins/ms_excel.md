# MS Excel

| | |
|---|---|
| Plugin ID | `ms_excel` |
| Plugin FQN | `OMNATA__MS_EXCEL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/ms_excel/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `single_file`, `multi_file` (Multi-File Individual) or `multi_file_consolidated` (Multi-File Consolidated).
- `header_row` (optional, default `1`): the row containing column headers.
- Single file: `spreadsheet_url` (required, SharePoint link) and `selected_file` (required, the Excel file chosen from that location).
- Multi-file modes: `parent_folder_url` (required) and `filename_pattern` (optional regex). `primary_key_columns` (optional) is offered in one of the multi-file modes.
- `header_row_preview` and `matched_files_preview` are display-only preview fields.

**Streams**: dynamic, depend on `sync_mode`. Single file lists one stream per worksheet, named after the sheet (CSV files use the filename without extension). Multi-File Individual lists one stream per matched file, named after the file. Multi-File Consolidated lists a single stream `MultipleFiles`. Worksheet and CSV streams have no source-defined primary key or cursor, so supply `STREAM_PRIMARY_KEYS` if you want merge semantics.

**Sync strategies supported**: worksheet and CSV streams are Full Refresh only. Multi-file streams support Full Refresh and Incremental.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'ms_excel-inbound',
    SYNC_NAME          => 'MS Excel to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<worksheet_name>'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('sync_mode', 'single_file', 'spreadsheet_url', '<sharepoint_link>', 'selected_file', '<file_id>', 'header_row', '1'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Replace`: clears the worksheet's existing contents and writes the Snowflake data in full.

**Sync parameters** (`SYNC_PARAMETERS`):
- `workbook_filter` (optional): narrows the workbook list.
- `spreadsheet_id` (required): the target Excel workbook.
- `worksheet_name` (required): the target worksheet.
- `preserve_column_order` (optional): keep the original column order of the source.

**Field mappings** (`FIELD_MAPPINGS`): none. The outbound form defines no mapper, so the source columns are written as-is.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Requires Microsoft Graph permissions on each SharePoint site. Outbound needs `Sites.ReadWrite.All` / `Files.ReadWrite.All` (or per-site write role); inbound only needs read.
- Excel has no change events. Rows deleted from a file only disappear after a Full Refresh.
- The `selected_file` value is a file identifier from a dynamic dropdown; copy it from a UI-created sync.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/ms_excel/README.md` (agrees on Replace outbound).
- Not verified: which multi-file mode exposes `primary_key_columns`, the exact `selected_file` value format, and whether the docs describe the mode values identically.
