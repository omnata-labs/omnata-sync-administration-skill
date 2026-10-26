# Hubspot

| | |
|---|---|
| Plugin ID | `hubspot` |
| Plugin FQN | `OMNATA__HUBSPOT` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/hubspot/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `include_associations` (required checkbox): fetch object associations with each record. Expensive on incremental runs, since changed objects are fetched individually.
- `check_archive` (required checkbox): fetch archived objects and mark them deleted. Adds extra API calls.
- `include_form_submissions` (required checkbox): adds one `form_submissions_<form_name>` stream per HubSpot form.
- `associations_warning` is a read-only information box, do not pass it.

**Streams**: partly static, partly dynamic. Static CRM objects: `companies`, `contacts`, `deals`, `tickets`, `line_items`, `products`, `quotes`, `leads`, `feedback_submissions`, engagements `calls`, `emails`, `meetings`, `notes`, `tasks`, plus `owners`, `users`, `teams`, `deal_pipelines`, `ticket_pipelines`, `forms`. Custom objects are discovered from the account's schema API. Form submission streams appear only when `include_form_submissions` is true. All streams have a source-defined primary key. `forms` has no cursor.

**Sync strategies supported**: CRM objects, custom objects and form submissions support `Incremental` and `Full Refresh`. `owners`, `users`, `teams`, `deal_pipelines`, `ticket_pipelines` and `forms` are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'hubspot-inbound',
    SYNC_NAME          => 'Hubspot to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['contacts', 'companies', 'deals', 'owners'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'include_associations', false,
                            'check_archive', false,
                            'include_form_submissions', false),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`):
- `Object Records`: `Create`, `Upsert`, `Update`. Used as the default if no target type is set.
- `Association Delete`: `Delete`.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: create new records.
- `Upsert`: create or update, matched on the chosen ID field.
- `Update`: update existing records only, matched on the chosen ID field.
- `Delete`: remove associations (Association Delete target only).

**Sync parameters** (`SYNC_PARAMETERS`): no fields are flagged required in code.
- Object Records: `hubspot_object` (target object), `hubspot_id_field` (record ID or a unique property such as email), `marketable_contact` (marketing status for imported contacts), `cleanup_default_associations` (remove default associations HubSpot adds after labelled association removal), `clear_null_field_values` (default false, explicitly clears nulls via an extra API pass).
- Association Delete: `from_object_type`, `to_object_type`.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`. Object Records targets are dynamic, loaded from the properties of `hubspot_object` (association targets appear as extra mapping options and take OBJECT columns). Association Delete has a static list with two required targets, `from_id` and `to_id`.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Outbound uses HubSpot import jobs, so the private app needs the `crm.import` scope. Dates are formatted `MM/DD/YYYY`. Tuning parameter `import_wait_time` (default 10 mins) controls import timeout.
- HubSpot does not bump last-modified dates on association changes, so incremental syncs with `include_associations` can miss association-only changes.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/hubspot/README.md`
- Docs list "<object> Archived" streams (for example "Deals Archived"). Code has no such streams, archived records are handled by `check_archive`. Code is followed here.
- Checkbox values are compared to the string `"True"` in code. Whether a boolean or string should be passed via the API was not verified. Copy from a UI-created sync if unsure.
