# Xero

| | |
|---|---|
| Plugin FQN | `OMNATA__XERO` |
| Page | `xero.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `tenants` (required, multi-select): the Xero organisations to read from.
- `api_sets` (required, multi-select, default `accounting`): `accounting` and/or `assets`. This sets the stream list.

**Streams**: dynamic, generated from the selected API sets, e.g. `accounts`, `contacts`, `invoices`. Some streams depend on parent streams.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `tenant` (required): the single tenant to write to.
- `api_set` (required, default `accounting`).
- `target_object` (required, depends on `api_set`): a top-level object.

**Field mappings**: `field_mapping_selector`, based on `target_object`. Only a single `contacts` field is currently mappable.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Multi-select values are comma-separated strings, for multiple tenants or API sets.
- Outbound appears experimental. Treat it as limited to contact creation.
- Only the `accounting` and `assets` API sets are offered, despite Payroll and Projects in the docs.
