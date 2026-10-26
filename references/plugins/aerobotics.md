# Aerobotics

| | |
|---|---|
| Plugin ID | `aerobotics` |
| Plugin FQN | `MONITORIAL__AEROBOTICS` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/aerobotics/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: Static list, for example `farms`, `farms_all`, `orchards`, `seasons`, `bins`, `surveys`, `fruit_sizes_bins`. Every stream has a source-defined primary key (its id field) and `source_defined_cursor` true. Some streams declare a dependency on a parent stream, so select parents alongside children.

**Sync strategies supported**: All streams support `Full Refresh`. Streams with a default cursor field (for example `captured_at` on the fruit size streams, `date` on survey streams) also support `Incremental`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'aerobotics-inbound',
    SYNC_NAME          => 'Aerobotics to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['farms', 'orchards', 'surveys', 'fruit_sizes_bins'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Requires the Aerobotics Enterprise API add-on for the access token to work.
- Insurance module streams mentioned in docs are not in the plugin stream list.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/aerobotics/README.md`
- Conflict: docs omit `farms_all`, which exists in code. Exact per-stream dependency map and cursor list not fully verified.
