# Salesforce Marketing Cloud

| | |
|---|---|
| Plugin FQN | `OMNATA__SFMC` |
| Page | `sfmc.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `stream_type` (required): `data_extension`, `journey_history` or `tracking_extract`. Changes the stream list and other fields.
- `activity_types` and `statuses` (required for journey history, multi-select).
- `data_extension_filter` (`filter` or `all`) and `data_extension_filter_text` (required when `filter`): limit the listed Data Extensions.
- `account_id` (optional, data extensions): overrides the connection's Account ID.
- `use_ftp_for_export` (SFTP methods) and `auto_fix_csv` (optional, data extensions).

**Streams**: one per Data Extension, or one per journey for journey history. Tracking extract has a fixed list (e.g. `Bounces`, `Clicks`). Data Extensions without primary key fields need `STREAM_PRIMARY_KEYS`. A Data Extension supports Incremental only when it has exactly one primary key field.

## Outbound

> **Warning: data loss and third-party sharing.** Outbound syncs send Snowflake data, including any personal data in the mapped columns, to Salesforce Marketing Cloud. `Replace` and `Mirror` permanently overwrite or delete Data Extension rows. Tell the user this before configuring an outbound sync.

**Sync parameters** (`SYNC_PARAMETERS`):
- `data_extension_name` (required): the target Data Extension. The stored value carries option metadata, so copy it from an existing sync rather than building it.
- `create_if_missing` (optional, default false): create the Data Extension if it doesn't exist.
- `account_id` (optional): overrides the connection's Account ID.

**Field mappings**: `field_mapping_selector`. Targets are the chosen Data Extension's columns, and new columns can be created. A primary key mapping is required, even for Replace.

**Before running**: `Replace` overwrites the Data Extension contents. `Mirror` deletes rows that are no longer in the source. This can't be undone. Show the user what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Outbound and tracking extract need an SFTP or Cloud Storage connection method. Tracking extract also appears on the OAuth for APIs method but fails there.
- Cloud Storage tracking extracts use the connection's `snowflake_stage` and `file_location_external_key`.
- The plugin's UDFS schema has helper functions that take `CONNECTION_PARAMETERS` first: `FETCH_DATA_EXTENSION_FOLDERS`, `GET_SEND_SUMMARY`, `GET_JOURNEY_DEFINITION` and `ENSURE_TRIGGERED_SEND`.

> **Warning: `SEND_TRIGGERED_EMAIL` emails real people.** Recipient personal data (email addresses, names and any fields in the message) is sent to Salesforce Marketing Cloud, and sent emails can't be recalled. Confirm the recipients and content with the user, and wait for their explicit yes before calling it.
