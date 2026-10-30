# Zoho CRM

| | |
|---|---|
| Plugin FQN | `OMNATA__ZOHO_CRM` |
| Page | `zoho_crm.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**:
  - `OAuth (Server based)`: authorization code security integration. Token endpoint is `/oauth/v2/token` and auth endpoint is `/oauth/v2/auth` on the Zoho accounts domain. Scopes: `ZohoCRM.bulk.ALL`, `ZohoCRM.settings.modules.READ`, `ZohoCRM.settings.fields.READ`, `ZohoCRM.org.READ`, `ZohoFiles.files.ALL`, `ZohoCRM.modules.ALL`, `offline_access`.
  - `OAuth (Self client)`: `client_id`, `client_secret` (secret), `initial_code` (secret, a temporary code from the Zoho self client app). No security integration template.
- **Common fields** (both methods, all required): `data_center_domain` (e.g. `www.zohoapis.com`, `.eu`, `.com.au`), `product_edition`, `user_count` (default 100), `addon_credits` (default 0). The last three set the rate limit quota.
- The correct `data_center_domain` is required.

## Inbound

**Sync parameters**: None, pass `OBJECT_CONSTRUCT()`.

**Streams**: dynamic, one per API-supported, visible Zoho module, named by module API name, e.g. `Leads`, `Contacts`. Records are read via the Zoho Bulk Read API. Incremental syncs also fetch deletions and return them with `IS_DELETED = TRUE`. Full Refresh doesn't fetch deletions.

## Outbound

> **Warning: changes records in Zoho CRM.** Outbound syncs send Snowflake data, including any personal data in the mapped columns, to Zoho CRM and create or update records there. Tell the user this, and confirm the module and fields, before configuring an outbound sync.

Outbound creates and changes records in Zoho CRM.

**Sync parameters** (`SYNC_PARAMETERS`):
- `module`: the target Zoho module.
- `find_by` (Update and Upsert only, depends on `module`): the unique field used to match existing records.

**Field mappings**: `field_mapping_selector`, with fields fetched for the chosen module. System-mandatory fields and the `find_by` field are required.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Outbound uses the Zoho Bulk Write API in batches of 25,000 records, concurrency 5.
- The plugin app's `UDFS` schema has consumer UDTFs. Each takes a connection object first, built with the plugin app's `PLUGIN.PLUGIN_CONNECTION` function and the connection slug.
  - `CREATE_RECORDS` takes a module name and an array of records keyed on field API name, and returns `ID`, `STATUS`, `RESULT`. **Before running**: it creates records in Zoho CRM. Confirm the module and records with the user before using it.
  - `SEARCH_RECORDS` takes a module name and criteria such as (Last_Name:equals:Smith), and returns `ID`, `RECORD`.
  - `DELETE_RECORDS` takes a module name and an array of record IDs, and returns `ID`, `STATUS`, `RESULT`. **Before running**: records go to the Zoho recycle bin. Show the user the module, record IDs and count, and confirm with the user before using it.
