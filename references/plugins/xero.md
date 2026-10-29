# Xero

| | |
|---|---|
| Plugin ID | `xero` |
| Plugin FQN | `OMNATA__XERO` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/xero/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `tenants` (required, multi-select dynamic dropdown): Xero organisations to read from.
- `api_sets` (required, multi-select, default `accounting`): `accounting` and/or `assets`. Determines the stream list.

**Streams**: dynamic, generated from the models in the selected `api_sets`. Representative (accounting): `accounts`, `contacts`, `invoices`, `payments`, `bank_transactions`. Some streams depend on parent streams. Primary keys may be composite.

**Sync strategies supported**: every stream supports `Full Refresh`. `Incremental` is added only where the model (or its parent) supports it.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'xero-inbound',
    SYNC_NAME          => 'Xero to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['accounts', 'contacts', 'invoices'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('tenants', '<tenant_id>', 'api_sets', 'accounting'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: creates new records. Upsert and Mirror are not supported.

**Sync parameters** (`SYNC_PARAMETERS`):
- `tenant` (required): single tenant to write to.
- `api_set` (required, default `accounting`).
- `target_object` (required, depends on `api_set`): top-level objects (no child models).

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, dynamic on `target_object`. Code currently filters mappable fields to a single field named `contacts`, noted as "all that's been tested".

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Multi-select values are read with `.split(",")`, so multiple tenants or api sets are comma-separated strings.
- Outbound appears experimental; treat as limited to contact creation.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/xero/README.md`
- Conflict: docs list Payroll and Projects ("Coming Soon"); the plugin offers only `accounting` and `assets`.
- Not verified: exact stored format for multi-select `tenants`; full stream name list.
