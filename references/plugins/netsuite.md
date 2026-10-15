# NetSuite

| | |
|---|---|
| Plugin ID | `netsuite` |
| Plugin FQN | `OMNATA__NETSUITE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/netsuite/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`. Throughput settings (`max_concurrent_streams`, `jdbcSetFetchSize` and others) are tuning parameters, not sync parameters.

**Streams**: Dynamic. Streams are the SuiteAnalytics Connect tables discovered from NetSuite's `OA_TABLES` catalog, named by table name (for example `transaction`, `customer`, `item`, plus `customrecord*`, `customlist*` and `map_*` tables). Primary keys come from an internal list for system tables, `id` for custom record/list and `usernote` tables, and `mapone`/`maptwo` for `map_*` tables. Tables outside those patterns may have no source-defined primary key and need `STREAM_PRIMARY_KEYS`.

**Sync strategies supported**: Tables with a modification-tracking cursor column support `Incremental` and `Full Refresh`. Tables without one support `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'netsuite-inbound',
    SYNC_NAME          => 'NetSuite to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['transaction', 'customer', 'item'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Requires the NetSuite JDBC driver to be installed and network access on TCP port 1708 (see docs).
- First stream listing reads `OA_TABLES` and can take several minutes on large instances.
- NetSuite enforces a per-account concurrent connection limit. Keep `max_concurrent_streams` well below it.
- `map_*` tables for multi-select relationships are not auto-selected. Add them to `STREAM_NAMES` explicitly.

## Sources

- Code: `omnata-labs/plugin-netsuite` at `src/plugin.py`, `src/metadata.py` (`build_streams_data`), `src/metadata_system_static.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/netsuite/README.md`
- Exact casing of discovered table names depends on the live `OA_TABLES` catalog. The example names are taken from the static system table list in code and were not checked against a live account.
