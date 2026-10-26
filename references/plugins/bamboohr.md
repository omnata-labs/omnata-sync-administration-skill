# BambooHR

| | |
|---|---|
| Plugin ID | `bamboohr` |
| Plugin FQN | `MONITORIAL__BAMBOOHR` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/bamboo_hr/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: Dynamic. `company_information` and `employees` are always present, and one stream per employee-related table is generated from the BambooHR tabular fields metadata endpoint, so the list varies by account. Every stream has a source-defined primary key (`legalName` for company information, `id` otherwise).

**Sync strategies supported**: `Full Refresh` only. All stream definitions set `supports_incremental = False`, so there are no default cursors.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'bamboohr-inbound',
    SYNC_NAME          => 'BambooHR to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['company_information', 'employees'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- The API key user's BambooHR permissions determine which fields and employees are visible.
- Table stream names come from the account's metadata, so list streams before hard-coding names.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/bamboo_hr/README.md`
- Exact naming of generated table streams not verified.
