# Google Sheets

| | |
|---|---|
| Plugin ID | `google_sheets` |
| Plugin FQN | `OMNATA__GOOGLE_SHEETS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/google_sheets/README.md` |

## Connection

Follow `configure-connections.md`. Google Sheets specifics:

**Methods** (from `CONNECTION_FORM()`):

| Method | Fields | OAuth |
|---|---|---|
| `Service Account` | `service_account_json` (secret, required): the JSON key file contents | No |
| `OAuth` | None | `authorization_code`, `CLIENT_SECRET_POST` |

**Where to get it:**

| Method | Where to get it |
|---|---|
| OAuth | [Google Cloud Console, Credentials](https://console.cloud.google.com/apis/credentials): create an OAuth client ID of type "Web application", and add both Snowflake redirect URIs (Step 3b of `configure-connections.md`) under Authorized redirect URIs. Enable the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) and [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) on the project |
| Service Account | [Google Cloud Console, Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts): create a service account, then on the Keys tab use Add key, Create new key, JSON, which downloads a `.json` file. Enable the Sheets and Drive APIs (links above). Key creation may be blocked by org policy |

**App-side access (Service Account):** share each Google Sheet with the service account's email (`client_email` in the key, ends in `.iam.gserviceaccount.com`), as Viewer for inbound or Editor for outbound. Without this the sync can't see the sheet.

**Service Account credentials:**

```sql
CALL OMNATA_SYNC_ENGINE.API.UPDATE_CONNECTION_OBJECTS(
    <CONNECTION_IN_PROGRESS_ID>,
    OBJECT_CONSTRUCT(),
    OBJECT_CONSTRUCT('service_account_json', OBJECT_CONSTRUCT('value', $$<PASTE THE ENTIRE KEY FILE CONTENTS HERE>$$)),
    OBJECT_CONSTRUCT()
);
```

For the secure path, store the key with `cortex secret store <key> --from-file <path>.json`. Before sending, check the stored value parses as JSON, that `type` is `service_account` and `private_key` is present, and show the user `client_email`.

**OAuth values** (from the plugin's template):

```sql
CALL OMNATA_SYNC_ENGINE.API.UPDATE_CONNECTION_OBJECTS(
    <CONNECTION_IN_PROGRESS_ID>,
    OBJECT_CONSTRUCT(),
    OBJECT_CONSTRUCT(),
    OBJECT_CONSTRUCT(
        'oauth_grant', 'authorization_code',
        'oauth_client_id', '<CLIENT_ID>',
        'oauth_client_secret', '<CLIENT_SECRET>',
        'oauth_token_endpoint', 'https://oauth2.googleapis.com/token',
        'oauth_authorization_endpoint', 'https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent',
        'oauth_allowed_scopes', ARRAY_CONSTRUCT(
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.metadata.readonly'),
        'oauth_client_auth_method', 'CLIENT_SECRET_POST'
    )
);
```

- The authorization endpoint contains `&prompt=consent`, so the secure path needs `--enable-templating STANDARD`.
- Google client secrets start with `GOCSPX-`. Redact output with `sed -E 's/GOCSPX-[A-Za-z0-9_-]+/[REDACTED]/g'`.
- The login link opens Google's consent screen. General Google guidance, not tested here: if the OAuth app's consent screen is in Testing mode, the user's Google account must be added as a test user.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `single_file` (default), `multi_file` (Multi-File Individual) or `multi_file_consolidated` (Multi-File Consolidated). Controls which fields below apply and how streams are built.
- `shared_with_me` (optional, default false): restrict spreadsheet listing to the Drive `sharedWithMe` filter.
- `search_all_drives` (optional, default true): include all shared drives in file search.
- `spreadsheet_id` (required in `single_file`): the spreadsheet to sync, chosen from a dynamic list.
- `parent_folder_id` (required in both multi-file modes): Drive folder URL or ID.
- `filename_pattern` (required in both multi-file modes): case-insensitive regex for spreadsheet names.
- `primary_key_columns` (optional): comma-separated column names applied as the source-defined primary key.
- `header_row` (optional, default `1`): 1-indexed header row. Rows above are skipped.
- `matched_files_preview` and `header_row_preview` are read-only preview fields, do not pass them.

**Streams**: always dynamic, read from Drive at configuration time. `single_file`: one stream per sheet (tab) in the workbook, named after the sheet. `multi_file`: one stream per matched spreadsheet, named after the spreadsheet (duplicates get a ` (n)` suffix). `multi_file_consolidated`: a single stream named `MultipleFiles`. Streams have no source-defined primary key unless `primary_key_columns` is set, and no default cursor field. Tab names with spaces and hyphens work as stream names as they are. The Sync Engine API has no procedure for listing a spreadsheet's tabs, so ask the user for the exact tab name (and a unique key column) when they give a spreadsheet.

**Sync strategies supported**: `single_file` streams are `Full Refresh` only. Multi-file streams support `Full Refresh` and `Incremental`.

**Primary keys are required:** every stream needs one, whatever the storage behaviour. Without it, `CONFIGURE_OMNATA_INBOUND_SYNC` fails with `Stream <tab> requires a primary key to be specified`, even with `append`. Pass the key column twice, as the `primary_key_columns` sync parameter and in `STREAM_PRIMARY_KEYS`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'google_sheets-inbound',
    SYNC_NAME          => 'Google Sheets to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<tab name>'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'sync_mode', 'single_file',
                            'spreadsheet_id', '<spreadsheet_id>',
                            'primary_key_columns', '<key column>',
                            'header_row', '1'),
    STREAM_PRIMARY_KEYS => OBJECT_CONSTRUCT('<tab name>', '<key column>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

`<spreadsheet_id>` is the long ID in the sheet's URL, between `/d/` and `/edit`.

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Replace`: writes the full Snowflake dataset into the chosen sheet, optionally clearing it first.

**Sync parameters** (`SYNC_PARAMETERS`): none are marked required in code, but the sync needs a target.
- `shared_with_me`, `search_all_drives`: same listing filters as inbound.
- `spreadsheet_id`: target spreadsheet. `sheet_name`: target sheet within it (depends on `spreadsheet_id`).
- `value_input_option`: `RAW` (default) or `USER_ENTERED`.
- `include_headers`: write a header row.
- `clear_sheet` (default true): clear the sheet before writing.
- `preserve_column_order` (default false): use the source/mapping column order.

**Field mappings** (`FIELD_MAPPINGS`): the outbound form defines no field mapping selector or Jinja template. Source columns are written directly. Stored field mappings are only read for column order when `preserve_column_order` is true.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Sheets must be table-shaped (header row, no merged cells, no blank rows or columns in the data range). If not, the run fails with an error like `1 columns passed, passed data had 2 columns`, meaning the header row has fewer named columns than the data. Fixes: set `header_row` to the real header row, name every column, or unmerge header cells. It can take more than one pass: each run reports the next mismatch. Ctrl/Cmd+End in the sheet jumps to the last used cell, which finds stray values in unnamed columns. After fixing headers, refresh the schema with `REFRESH_INBOUND_STREAM_SCHEMAS` before rerunning.
- The stream list depends on `sync_mode` and the file parameters, so set those before choosing streams.
- **Columns are detected from the first data row, not the header.** Empty cells at the end of that row are dropped, so a new column that's sparsely filled never reaches the schema or the normalized view. Have the user fill in row 2 (the first data row) for every column, then run `REFRESH_INBOUND_STREAM_SCHEMAS` and `RECREATE_INBOUND_NORMALIZED_VIEWS`.
- **`Primary key field '<x>' was not present in all records`:** the key column isn't on that sheet. Update both `primary_key_columns` and `STREAM_PRIMARY_KEYS` to a column that is. Watch for keys copied over from another sheet's sync.

## Sources

- Code: `omnata-labs/plugin-google-sheets` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/google_sheets/README.md`
- Docs list Full Refresh as the only inbound strategy. Code allows Incremental for multi-file modes. Code is followed here.
- Docs describe `primary_key_columns` as Multi-File Individual only. Code shows the field in all modes.
