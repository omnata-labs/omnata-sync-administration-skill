# Salesforce

| | |
|---|---|
| Plugin FQN | `OMNATA__SALESFORCE` |
| Page | `salesforce.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`), all optional. Pass `OBJECT_CONSTRUCT()` to accept defaults.
- `include_formula_fields`: calculate formula fields in Snowflake. Needs the `CustomField` stream in the same sync.
- `incremental_timestamp_offset`: seconds subtracted from the last cursor value (max useful value 600).
- `currency_rounding`: round currency and percent fields in normalized views to their Salesforce scale.

**Streams**: one per queryable sObject, named by API name (e.g. `Account`, custom objects ending in __c). Change Data Capture event objects are excluded.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `salesforce_object` (required): the target object.
- `salesforce_id_field` (required for Upsert and Mirror): the External ID field used as the match key.
- `serial_mode`, `apply_null_values`, `retry_locked_records` (optional checkboxes, not shown for Record Merge or Delete).
- `assignment_rule_name` (optional, where applicable): the Assignment Rule to apply.

**Field mappings**: `field_mapping_selector`. Targets come from the chosen `salesforce_object`. Update needs an APP_IDENTIFIER (Record ID) mapping. Delete needs a single Record ID field mapping. Record Merge needs Target RecordID Field and Source RecordIDs Field mappings. Update needs the 18 character Salesforce Id.

**Before running**: `Delete` removes records in Salesforce. `Mirror` overwrites records to match Snowflake, including removing values. `Record Merge` merges records (Lead, Contact, Account, Individual). None can be undone without a backup. Confirm with the user before using it.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- SOAP-style REQUEST_LIMIT_EXCEEDED responses (HTTP 403) are retried as rate limits. Treat them as throttling, not a permissions error.
- Tag objects (ending in __Tag) use `SystemModstamp` as the cursor.
