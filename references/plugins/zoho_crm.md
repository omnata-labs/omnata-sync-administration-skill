# Zoho CRM

| | |
|---|---|
| Plugin ID | `zoho_crm` |
| Plugin FQN | `OMNATA__ZOHO_CRM` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/zoho_crm/README.md` |

## Connection

Follow `configure-connections.md`.
- **Methods**: `OAuth (Server based)` (authorization code security integration; template scopes `ZohoCRM.bulk.ALL`, `ZohoCRM.settings.modules.READ`, `ZohoCRM.settings.fields.READ`, `ZohoCRM.org.READ`, `ZohoFiles.files.ALL`, `ZohoCRM.modules.ALL`, `offline_access`; token/auth endpoints `https://<accounts domain>/oauth/v2/token` and `/oauth/v2/auth`) and `OAuth (Self client)` (fields `client_id`, `client_secret` (secret), `initial_code` (secret, temporary code from the Zoho self client app); no security integration template).
- **Common fields** (both methods, all required): `data_center_domain` (dropdown: `www.zohoapis.com`, `.com.au`, `.eu`, `.in`, `.com.cn`, `.jp`), `product_edition` (`free`, `standard_starter`, `professional`, `enterprise`, `ultimate`), `user_count` (default `100`), `addon_credits` (default `0`). The last three set the rate limit quota.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: dynamic, one per Zoho module that is API-supported and visible. Stream names are module API names, e.g. `Leads`, `Contacts`, `Accounts`, `Deals`. All streams use primary key `Id` and default cursor `Modified_Time`.

**Sync strategies supported**: `Incremental` and `Full Refresh` for all streams. Records are read via the Zoho Bulk Read API. Incremental syncs also fetch deletions from the deleted records API and return them with `IS_DELETED = TRUE` (record data `Id`, `Deleted_Time`, `Deletion_Type`), tracked with a separate `max_deleted_time` cursor alongside `max_modified_time`. Full Refresh does not fetch deletions.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'zoho_crm-inbound',
    SYNC_NAME          => 'Zoho CRM to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['Leads', 'Contacts', 'Accounts'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: inserts records (Zoho bulk write operation `insert`).
- `Update`: updates records matched on `find_by`.
- `Upsert`: inserts or updates records matched on `find_by`.

**Sync parameters** (`SYNC_PARAMETERS`):
- `module` (dynamic dropdown): target Zoho module.
- `find_by` (Update and Upsert only, depends on `module`): unique field used to match existing records.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, fields fetched dynamically for the chosen module. System-mandatory fields and the `find_by` field are marked required.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Outbound uses the Zoho Bulk Write API in batches of 25,000 records, concurrency 5.
- Connection requires the correct `data_center_domain`; bulk writes use the Zoho `org_id`, fetched from the API if not stored on the connection.
- Consumer UDTFs in the plugin app's `UDFS` schema, each taking a connection object first (`<plugin_app>.PLUGIN.PLUGIN_CONNECTION('<connection_slug>')`):
  - `CREATE_RECORDS(CONNECTION_PARAMETERS OBJECT, MODULE_NAME VARCHAR, RECORDS ARRAY)` returns `ID, STATUS, RESULT`; records are objects keyed on field API name.
  - `SEARCH_RECORDS(CONNECTION_PARAMETERS OBJECT, MODULE_NAME VARCHAR, CRITERIA VARCHAR)` returns `ID, RECORD`; criteria like `(Last_Name:equals:Smith)`.
  - `DELETE_RECORDS(CONNECTION_PARAMETERS OBJECT, MODULE_NAME VARCHAR, RECORD_IDS ARRAY)` returns `ID, STATUS, RESULT`; records go to the Zoho recycle bin.
  - Example: `SELECT ID, STATUS FROM TABLE(<plugin_app>.UDFS.CREATE_RECORDS(<plugin_app>.PLUGIN.PLUGIN_CONNECTION('<connection_slug>'), 'Leads', PARSE_JSON('[{"Last_Name":"<name>"}]')::ARRAY));` `STATUS` is `success` per successful record.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/zoho_crm/README.md` (agrees: no inbound configuration fields)
- Not verified: whether `module` and `find_by` are required. Example stream names are standard Zoho module API names; actual list depends on the org. `<plugin_app>` is the installed plugin application name (not verified as a fixed value).
