# Notion

| | |
|---|---|
| Plugin FQN | `OMNATA__NOTION` |
| Page | `notion.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `what_to_sync` (required): `objects` (default) or `database_records`. Changes the stream list.
- `walk_data_source_rows` (optional, objects mode only, default false): extends the blocks, block content, comments and comment content streams to database rows. Costs one API request per row.

**Streams**: objects mode has a fixed list (e.g. `pages`, `blocks`). Database records mode creates one stream per Notion database shared with the integration, named from the database title.

## Notes

- Notion allows about 3 requests per second per connection. Turning on `walk_data_source_rows` can make syncs much slower.
- To get database rows plus page content, create one sync per mode and join them downstream.
- Only pages and databases explicitly shared with the integration are visible.
- With a PAT, the `users` stream returns no results.
- The stored format of `what_to_sync` (plain string or option object) is unconfirmed. Copy it from a UI-created sync if unsure.
