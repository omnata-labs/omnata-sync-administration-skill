# Notion

| | |
|---|---|
| Plugin ID | `notion` |
| Plugin FQN | `OMNATA__NOTION` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/notion/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `what_to_sync` (required): `objects` (default) or `database_records`. Changes the stream list.
- `walk_data_source_rows` (optional, Objects mode only, default false): extends the `blocks`, `block_content`, `comments` and `comment_content` streams to database rows. Costs one API request per row.

**Streams**: Depends on `what_to_sync`.
- `objects`: static list of seven streams: `users`, `data_sources`, `pages`, `comments`, `comment_content`, `blocks`, `block_content`.
- `database_records`: dynamic, one stream per Notion database shared with the integration, named from the database title (slugified).
All streams have source-defined primary key `id`. Only incremental streams have a default cursor.

**Sync strategies supported**: In Objects mode only `pages` supports `Incremental`; the rest are `Full Refresh` only. All database record streams support `Incremental` and `Full Refresh`.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'notion-inbound',
    SYNC_NAME          => 'Notion to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['pages', 'blocks', 'block_content', 'users'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('what_to_sync', 'objects'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Notion allows about 3 requests per second per connection. Enabling `walk_data_source_rows` can make syncs much slower.
- To get database rows plus page content, create one sync per mode and join downstream.
- Only pages and databases explicitly shared with the integration are visible.
- With a PAT, the `users` stream returns no results (per docs).

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/notion/README.md`
- The exact value format of `what_to_sync` when stored by the UI (plain string versus option object) was not verified. Copy from a UI-created sync if unsure.
