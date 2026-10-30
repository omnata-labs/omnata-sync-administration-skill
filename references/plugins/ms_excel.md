# MS Excel

| | |
|---|---|
| Plugin FQN | `OMNATA__MS_EXCEL` |
| Page | `ms_excel.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Before you start**: the app needs Microsoft Graph permissions on each SharePoint site. Inbound needs read access. Outbound needs Sites.ReadWrite.All and Files.ReadWrite.All, or a write role on each site. See the docs.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `single_file`, `multi_file` (Multi-File Individual) or `multi_file_consolidated` (Multi-File Consolidated).
- `header_row` (optional, default `1`): the row that holds the column headers.
- Single file: `spreadsheet_url` (required, a SharePoint link) and `selected_file` (required, the Excel file chosen from that location).
- Multi-file modes: `parent_folder_url` (required) and `filename_pattern` (optional regex). One of the multi-file modes also offers `primary_key_columns` (optional).
- `header_row_preview` and `matched_files_preview` are display-only.

**Streams**: depend on `sync_mode`. Single file gives one stream per worksheet, named after the sheet. CSV files use the filename without its extension. Multi-File Individual gives one stream per matched file. Multi-File Consolidated gives one stream, `MultipleFiles`. Worksheet and CSV streams have no source-defined primary key or cursor, so set `STREAM_PRIMARY_KEYS` if you want merge.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `workbook_filter` (optional): narrows the workbook list.
- `spreadsheet_id` (required): the target workbook.
- `worksheet_name` (required): the target worksheet.
- `preserve_column_order` (optional): keeps the source column order.

**Field mappings**: none. Source columns are written as they are.

**Before running**: `Replace` clears the worksheet's contents, then writes the data in full. Existing worksheet data is lost. Show the user what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation. Name the workbook and worksheet.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Excel has no change events. Rows deleted from a file only disappear after a Full Refresh.
- `selected_file` is a file identifier from a dynamic dropdown. Copy it from a sync created in the UI.
