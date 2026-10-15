# Marketo

| | |
|---|---|
| Plugin ID | `marketo` |
| Plugin FQN | `OMNATA__MARKETO` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: No. Outbound: Yes |
| Docs | `apps/marketo/README.md` |

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Upsert`: create records that do not exist and update those that do, matched on the lookup or dedupe field.
- `Update`: update existing records only, matched on the lookup or dedupe field.
- `Create`: create new records only.

**Sync parameters** (`SYNC_PARAMETERS`):
- `marketo_object` (required): the Marketo object to sync to, loaded dynamically (`leads` plus custom objects). Reloads the form on change.
- `partition_name` (required when `marketo_object` is `leads`): the lead partition to write to.
- `lookup_field` (required for `leads` with Upsert or Update): the field used to match existing leads.
- `dedupe_by` (required for custom objects): `dedupeFields` or `marketoGUID`, the match method for existing records.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`. Target fields are dynamic, fetched from the Marketo describe for the chosen object. For leads, the field selected as `lookup_field` becomes a required mapping.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- The form is staged: no mapper is rendered until `marketo_object` is set, and the mapper depends on `lookup_field` or `dedupe_by` where those apply. Hand-built parameter sets must include every stage.
- Connection requires `client_id`, `client_secret` and `munchkin_id`.

## Sources

- Code: `omnata-labs/plugin-marketo` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/marketo/README.md`. Docs list only Leads (Create, Update, Upsert); code also offers custom objects via `dedupe_by`. Code wins.
- Not verified: the exact list of objects returned by `fetch_marketo_objects` at runtime, and the full set of required mappings for custom objects (lines around the mapper were not fully traced).
