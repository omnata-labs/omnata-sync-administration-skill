# Contentful

| | |
|---|---|
| Plugin ID | `contentful` |
| Plugin FQN | `OMNATA__CONTENTFUL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/contentful/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): Depend on the connection method.
- Content Delivery API connections: none, pass `OBJECT_CONSTRUCT()` (the connection is already scoped to one space and environment).
- Content Management API connections:
  - `organization` (required): Contentful organization ID (`sys.id`), chosen from a dynamic list.
  - `space_pattern` (required, default `.*`): regex on space names; only matching spaces are synced.
  - `environment_pattern` (required, default `.*`): regex on environment names; only matching environments are synced.

**Streams**: Static list, filtered by connection method. Content Management API: `assets`, `assets_published`, `content_types`, `entries`, `entries_published`, `environments`, `locales`, `memberships`, `spaces`, `tags`. Content Delivery API: only `assets`, `content_types`, `entries`, `locales`. All streams use primary key `id` and a source-defined cursor.

**Sync strategies supported**: All streams support `Incremental` and `Full Refresh`, except `locales` on Content Delivery API connections, which is `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'contentful-inbound',
    SYNC_NAME          => 'Contentful to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['entries', 'assets', 'content_types', 'locales'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
        'organization', '<organization_id>',
        'space_pattern', '.*',
        'environment_pattern', '.*'
    ),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

The example assumes a Content Management API connection. For a Content Delivery API connection, pass `OBJECT_CONSTRUCT()`.

## Notes

- Connection methods: "Content Delivery API" (`cda_token`, `space_id`, `environment_id`, optional `use_preview`) and "Content Management API" (`cma_token`). The method controls both the parameter form and the stream list.
- Organization IDs can be listed with the plugin's `UDFS.FETCH_ORGANIZATIONS` function (see docs).

## Sources

- Code: `plugin-contentful` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/contentful/README.md`
- Docs list only 8 streams and only describe CMA tokens. Code also has `entries_published` / `assets_published` and the Content Delivery API method; code wins.
