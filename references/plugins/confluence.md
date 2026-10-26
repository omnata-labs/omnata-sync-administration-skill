# Confluence

| | |
|---|---|
| Plugin ID | `confluence` |
| Plugin FQN | `OMNATA__CONFLUENCE` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/confluence/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `cql_pages_clause` (optional): extra CQL clause to filter pages, for example `space = DEV`. `order by` is not permitted.
- `cql_blogposts_clause` (optional): extra CQL clause to filter blog posts. `order by` is not permitted.

**Streams**: Static list of 8 streams: `pages`, `spaces`, `blog_posts`, `page_comments`, `page_attachments`, `content_labels`, `pages_content`, `users`. All have source-defined primary keys and source-defined cursors (no default cursor field is declared). `page_comments`, `page_attachments`, `content_labels` and `pages_content` depend on `pages`, so include `pages` in the same sync.

**Sync strategies supported**: `pages`, `blog_posts` and `pages_content` support `Incremental` and `Full Refresh`. The others are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'confluence-inbound',
    SYNC_NAME          => 'Confluence to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['pages', 'spaces', 'blog_posts', 'pages_content', 'users'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

To restrict to one space, add for example `'cql_pages_clause', 'space = DEV'` to `SYNC_PARAMETERS`.

## Notes

- Confluence Cloud only. Data Center/Server is not supported.
- Three connection methods: API Token (`site_name`, `username`, `api_token`), OAuth, and Service Account OAuth. Network access differs: the API token method calls the site domain, the OAuth methods call `api.atlassian.com` and `auth.atlassian.com`.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/confluence/README.md`
- Nothing material left unverified.
