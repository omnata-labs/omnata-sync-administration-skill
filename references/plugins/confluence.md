# Confluence

| | |
|---|---|
| Plugin FQN | `OMNATA__CONFLUENCE` |
| Page | `confluence.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: API Token (`site_name`, `username`, `api_token`; `api_token` is secret), OAuth, and Service Account OAuth.
- **Quirks**: the API Token method calls the site domain. The OAuth methods call `api.atlassian.com` and `auth.atlassian.com`, so network access differs.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `cql_pages_clause` (optional): an extra CQL clause to filter pages, for example `space = DEV`. `order by` isn't allowed.
- `cql_blogposts_clause` (optional): an extra CQL clause to filter blog posts. `order by` isn't allowed.

**Streams**: a static list (e.g. `pages`, `spaces`, `blog_posts`). Comments, attachments, labels and page content depend on `pages`, so include `pages` in the same sync.

## Notes

- Confluence Cloud only. Data Center and Server aren't supported.
