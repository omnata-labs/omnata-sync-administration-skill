# Airtable

| | |
|---|---|
| Plugin ID | `airtable` |
| Plugin FQN | `OMNATA__AIRTABLE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/airtable/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `base` (dropdown, dynamic list of bases; required in practice, since the stream list can't be built without it): the Airtable base ID to sync from.

**Streams**: Dynamic, one stream per table in the selected base, named by the table name. The primary key is the table's primary field name. No default cursor is defined.

**Sync strategies supported**: `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'airtable-inbound',
    SYNC_NAME          => 'Airtable to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<table_name>'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('base', '<base_id>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

> **Warning:** `Replace` replaces the target table's contents in full: existing records not in the Snowflake data are removed. Confirm the target table with the user before creating or running the sync.

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: insert new records.
- `Update`: update existing records.
- `Upsert`: create or update, matched on the table's primary field.
- `Replace`: full replacement of the table contents.

**Sync parameters** (`SYNC_PARAMETERS`):
- `base`: the target base ID (dynamic dropdown).
- `table_name`: the target table name (dynamic dropdown, depends on `base`).

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, populated dynamically from the chosen table's fields. Formula, rollup, lookup, system timestamp and multi-value fields are excluded. The table's primary field is a required mapping and is used as the upsert key.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Table names are used as stream names, so they can contain spaces and mixed case.
- Writes use Airtable batch upsert with typecast enabled.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/airtable/README.md`
- Conflict: docs say Incremental is supported for tables with a last modified time field; the plugin supports `Full Refresh` only.
