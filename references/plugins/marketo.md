# Marketo

| | |
|---|---|
| Plugin FQN | `OMNATA__MARKETO` |
| Page | `marketo.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`. The connection needs `client_id`, `client_secret` and `munchkin_id`.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `marketo_object` (required): the Marketo object to sync to, either `leads` or a custom object. Changing it reloads the form.
- `partition_name` (required for `leads`): the lead partition to write to.
- `lookup_field` (required for `leads` with Upsert or Update): the field used to match existing leads.
- `dedupe_by` (required for custom objects): `dedupeFields` or `marketoGUID`, the method used to match existing records.

**Field mappings**: `field_mapping_selector`. Target fields come from Marketo for the chosen object. For leads, the field chosen as `lookup_field` must be mapped.

Outbound syncs send Snowflake record data, such as lead details and email addresses, to Marketo. Confirm with the user which data is sent before creating or running the sync.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- The form is staged. No mapper appears until `marketo_object` is set, and the mapper depends on `lookup_field` or `dedupe_by` where they apply. A parameter set must include every stage.
