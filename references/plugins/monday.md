# Monday.com

| | |
|---|---|
| Plugin FQN | `DATA_ENGINEERS__MONDAY` |
| Page | `monday.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required, default `objects`): `objects` fetches Monday.com objects as streams; `boards` fetches each board as its own streams.
- Boards mode only: `workspace_id` (the workspace to list boards from), `workspace_state` (default `active`), `workspace_kind` (default `open`), `board_states` (default `active`), `board_ids` (optional, limits to specific boards and sub-boards).

**Streams**: objects mode has a fixed list (e.g. `boards`, `board_items`, `board_columns`). Boards mode creates one items stream per board, plus subitems streams, and lists nothing until `workspace_id` is set. "Incremental" doesn't mean delta fetching for most objects, because Monday.com has no change events.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`): `monday_object` (only `items`), `board` (the target board) and `group` (the target group on that board).

**Field mappings**: `field_mapping_selector`. Target fields are the chosen board's columns.

**Before running**: `Mirror` removes board items that are no longer in the source. Removed items can't be restored by Omnata. Show the user what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Outbound can only update or remove items that were created from Snowflake. Items created in Monday.com aren't touched.
- The developer is Monitorial, so the FQN prefix is `DATA_ENGINEERS`, not `OMNATA`.
