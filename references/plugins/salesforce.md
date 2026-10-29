# Salesforce

| | |
|---|---|
| Plugin ID | `salesforce` |
| Plugin FQN | `OMNATA__SALESFORCE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/salesforce/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`), all optional:
- `include_formula_fields`: calculate formula fields in Snowflake. Requires the `CustomField` stream in the same sync.
- `incremental_timestamp_offset`: seconds subtracted from the last cursor value (max useful value 600).
- `currency_rounding`: round currency/percent fields in normalized views to their Salesforce scale.
Pass `OBJECT_CONSTRUCT()` to accept defaults.

**Streams**: Dynamic, from Salesforce global `describe()`. One stream per queryable sObject, named by API name (for example `Account`, `Contact`, `Opportunity`, custom `*__c` objects). All have primary key `Id`. The cursor (for example `SystemModstamp`) is looked up per object; objects with no known cursor have none.

**Sync strategies supported**: Objects with a cursor support `Incremental` and `Full Refresh`; others `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'salesforce-inbound',
    SYNC_NAME          => 'Salesforce to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['Account', 'Contact', 'Opportunity'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

> **Warning:** `Delete` removes records in Salesforce, and `Mirror` overwrites them to match Snowflake, including removing values. Neither can be undone without a backup. Confirm the object and strategy with the user before creating or running the sync.

**Target types** (`OUTBOUND_TARGET_TYPE`):
- `Standard Object Records`: Create, Upsert, Update, Mirror, Delete.
- `Custom Object Records`: Create, Upsert, Update, Mirror, Delete.
- `Record Merge`: Record Merge.

**Strategies** (`SYNC_STRATEGY_NAME`): `Create`, `Upsert`, `Update`, `Mirror`, `Delete` (standard runtime behaviour), and custom `Record Merge` (calls Salesforce `merge()` once per new source record; Lead, Contact, Account, Individual).

**Sync parameters** (`SYNC_PARAMETERS`):
- `salesforce_object` (required): target object.
- `salesforce_id_field` (required for Upsert and Mirror): External ID field used as the match key.
- `serial_mode`, `apply_null_values`, `retry_locked_records` (optional checkboxes, not shown for Record Merge or Delete).
- `assignment_rule_name` (optional, Create/Update/Upsert/Mirror where applicable): Assignment Rule to apply.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`. Targets are fetched dynamically from the chosen `salesforce_object`. Delete requires a single `Record ID field` mapping. Record Merge requires `Target RecordID Field` and `Source RecordIDs Field` mappings. Update needs the 18 character Salesforce Id (per docs).

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Uses Bulk API with PK chunking where possible; tuning parameters (not sync parameters) include `initial_bulk_query_limit`, `pk_chunk_size` and `batch_size`, `batch_parallel_limit` (outbound). Inbound also has:
  - `max_concurrent_streams`: streams processed concurrently (1 to 64, default 2, capped at the number of streams in the run).
  - `skip_empty_objects_via_record_count` (default true): uses the approximate `limits/recordCount` API and marks streams with a count of 0 complete without querying. Objects missing from that API fall back to a `COUNT()` query.
  - `disable_secondary_field_incrementals` (default false): sort and page on the cursor field only, for objects whose bulk queries time out.
- SOAP-style `REQUEST_LIMIT_EXCEEDED` responses (HTTP 403) are retried as rate limits (429), inbound and outbound. Treat them as throttling, not a permissions error.
- `*__Tag` objects use `SystemModstamp` as the cursor.
- Change Data Capture `*ChangeEvent` objects are excluded from the stream list.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/salesforce/README.md`
- The exact conditions gating `assignment_rule_name` (object-specific checks after the strategy test) were not fully traced.
