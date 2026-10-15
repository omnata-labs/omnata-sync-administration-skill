# Monday.com

| | |
|---|---|
| Plugin ID | `monday` |
| Plugin FQN | `DATA_ENGINEERS__MONDAY` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/monday/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required, default `objects`): `objects` (fetch Monday objects as streams) or `boards` (fetch each board as streams).
- Boards mode: `workspace_state` (default `active`), `workspace_kind` (default `open`), `workspace_id` (the workspace to list boards from), `board_states` (default `active`), `board_ids` (optional, limit to specific board and sub-board IDs).

**Streams**: depend on `sync_mode`. Objects mode is a static catalog, for example `accounts`, `activity_logs`, `boards`, `board_columns`, `board_items`, `board_item_column_values`, `docs`, `folders`. Boards mode is dynamic: one `<board_name_snake_case>_<board_id>_items` stream per board (plus `_subitems` streams), and nothing is listed until `workspace_id` is set. Object streams use primary key `syncId` with a source-defined cursor and no default cursor field.

**Sync strategies supported**: object streams default to Full Refresh and Incremental unless the stream overrides it. Docs note that "Incremental" does not mean delta fetching for most objects, because Monday.com exposes no change events.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'monday-inbound',
    SYNC_NAME          => 'Monday.com to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['boards', 'board_items', 'board_columns'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('sync_mode', 'objects'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: create new items.
- `Upsert`: create or update items that originated from Snowflake.
- `Mirror`: keep the board in line with the source, including removals.

**Sync parameters** (`SYNC_PARAMETERS`):
- `monday_object` (the target object; only `items` is offered).
- `board` (required when `monday_object` is `items`): the target board.
- `group` (required, depends on `board`): the target group on that board.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, depends on `group`. Target fields are dynamic, taken from the chosen board's columns.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- Outbound only supports items that originate in Snowflake. Updating or deleting items created in Monday.com is not supported.
- Inbound tuning parameters include `max_concurrent_streams` (1 to 10, default 1), `max_retry_attempts`, `max_page_items` and `max_page_activity_logs`.
- Developer is Monitorial Ltd (`developer_id='data_engineers'`), so the FQN prefix is not `OMNATA`.

## Sources

- Code: `omnata-labs/plugin-monday` at `src/plugin.py`, `src/plugin_api_documents.py`, `src/inbound/stream_metadata.py`, `src/models/monday_object.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/monday/README.md` (agrees on Create, Upsert, Mirror and items only).
- Not verified: whether `monday_object` is marked required, the required flag on the boards-mode workspace fields, and the FQN (derived from `developer_id`, not observed in `PLUGIN_FQN`).
