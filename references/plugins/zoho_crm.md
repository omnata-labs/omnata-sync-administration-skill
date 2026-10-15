# Zoho CRM

| | |
|---|---|
| Plugin ID | `zoho_crm` |
| Plugin FQN | `OMNATA__ZOHO_CRM` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/zoho_crm/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: dynamic, one per Zoho module that is API-supported and visible. Stream names are module API names, e.g. `Leads`, `Contacts`, `Accounts`, `Deals`. All streams use primary key `Id` and default cursor `Modified_Time`.

**Sync strategies supported**: `Incremental` and `Full Refresh` for all streams. Records are read via the Zoho Bulk Read API.

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
- `Create`: inserts records.
- `Update`: updates records matched on `find_by`.
- `Upsert`: inserts or updates records matched on `find_by`.

**Sync parameters** (`SYNC_PARAMETERS`):
- `module` (dynamic dropdown): target Zoho module.
- `find_by` (Update and Upsert only, depends on `module`): unique field used to match existing records.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, fields fetched dynamically for the chosen module. System-mandatory fields and the `find_by` field are marked required.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Outbound uses the Zoho Bulk Write API in batches of 25,000 records, concurrency 5.
- Connection requires the correct `data_center_domain`; the connection also stores `org_id` used by bulk writes.

## Sources

- Code: `omnata-labs/plugin-zoho-crm` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/zoho_crm/README.md` (agrees: no inbound configuration fields)
- Not verified: `module` and `find_by` have no explicit `required=` flag. Example stream names are standard Zoho module API names; actual list depends on the org.
