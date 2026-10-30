# Google Sheets

| | |
|---|---|
| Plugin FQN | `OMNATA__GOOGLE_SHEETS` |
| Page | `google_sheets.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `Service Account` (field `service_account_json`, secret, required: the JSON key file contents) and `OAuth` (no fields).
- **Before you start**: enable the Google Sheets API and Google Drive API on the GCP project. For OAuth, create a Web application OAuth client and add both Snowflake redirect URIs. For Service Account, create a JSON key (org policy may block this). See the docs for the steps.
- **Sharing (Service Account)**: share each sheet with the service account's `client_email` (ends in .iam.gserviceaccount.com), as Viewer for inbound or Editor for outbound. Otherwise the sync can't see the sheet.
- **Service Account secret**: the key contains a private key. Use the Omnata UI route in `configure-connections.md` to enter it, so it stays out of query history. Tested: a connection started with `BEGIN_CONNECTION_CREATION` can be finished on the Google Sheets page of the Omnata UI.
- **OAuth values**: grant type `authorization_code`; client auth method `CLIENT_SECRET_POST`; token endpoint `https://oauth2.googleapis.com/token`; authorization endpoint `https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent`; scopes `https://www.googleapis.com/auth/spreadsheets` and `https://www.googleapis.com/auth/drive.metadata.readonly`.
- **Quirks**: the authorization endpoint contains `&`, so the secure path needs `--enable-templating STANDARD`. Never display a client secret. Google client secrets start with GOCSPX-; mask any value with that prefix that appears in a result. If the OAuth consent screen is in Testing mode, the user's Google account must be a test user (general Google guidance, not tested).

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `single_file` (default), `multi_file` or `multi_file_consolidated`. Controls which fields below apply and how streams are built.
- `shared_with_me` (optional, default false): only list spreadsheets shared with the user.
- `search_all_drives` (optional, default true): include shared drives in file search.
- `spreadsheet_id` (required in `single_file`): the long ID in the sheet URL, between /d/ and /edit.
- `parent_folder_id` (required in multi-file modes): Drive folder URL or ID.
- `filename_pattern` (required in multi-file modes): case-insensitive regex for spreadsheet names.
- `primary_key_columns` (optional): comma-separated column names used as the primary key.
- `header_row` (optional, default `1`): 1-indexed header row. Rows above it are skipped.
- `matched_files_preview` and `header_row_preview` are read-only. Don't pass them.

**Streams**: dynamic, read from Drive. `single_file` gives one stream per tab, named after the tab. `multi_file` gives one stream per matched spreadsheet. `multi_file_consolidated` gives one stream named `MultipleFiles`. Tab names with spaces and hyphens work as stream names. There is no API to list a spreadsheet's tabs, so ask the user for the exact tab name and a unique key column.

**Primary keys are required** for every stream, whatever the storage behaviour. Without one, `CONFIGURE_OMNATA_INBOUND_SYNC` fails with "requires a primary key to be specified", even with `append`. Pass the key column both as `primary_key_columns` and in `STREAM_PRIMARY_KEYS`.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `shared_with_me`, `search_all_drives`: same listing filters as inbound.
- `spreadsheet_id`: target spreadsheet. `sheet_name`: target sheet within it.
- `value_input_option`: `RAW` (default) or `USER_ENTERED`.
- `include_headers`: write a header row.
- `clear_sheet` (default true): clear the sheet before writing.
- `preserve_column_order` (default false): use the source or mapping column order.

**Field mappings**: none. Source columns are written directly. Stored mappings are only read for column order when `preserve_column_order` is true.

> **Warning: permanent data loss.** `Replace` permanently and irreversibly overwrites all existing data in the target sheet, and with `clear_sheet` clears it first. Omnata can't recover it. Show the user what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation. Name the spreadsheet and sheet.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Sheets must be table-shaped: a header row, no merged cells, no blank rows or columns in the data. Otherwise runs fail with an error like "1 columns passed, passed data had 2 columns", meaning the header has fewer named columns than the data. Fix by setting `header_row`, naming every column, or unmerging header cells. Each run reports the next mismatch. Ctrl/Cmd+End in the sheet finds stray values. Then run `REFRESH_INBOUND_STREAM_SCHEMAS` before rerunning.
- Set `sync_mode` and the file parameters before choosing streams.
- Columns are detected from the first data row, not the header. Empty cells at the end of that row are dropped, so a sparsely filled new column never reaches the schema. Have the user fill row 2 for every column, then run `REFRESH_INBOUND_STREAM_SCHEMAS` and `RECREATE_INBOUND_NORMALIZED_VIEWS`.
- "Primary key field was not present in all records" means the key column isn't on that sheet. Update both `primary_key_columns` and `STREAM_PRIMARY_KEYS`. Watch for keys copied from another sheet's sync.
