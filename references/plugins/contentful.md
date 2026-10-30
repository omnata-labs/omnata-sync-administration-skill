# Contentful

| | |
|---|---|
| Plugin FQN | `OMNATA__CONTENTFUL` |
| Page | `contentful.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: Content Delivery API (`cda_token` secret, `space_id`, `environment_id`, optional `use_preview`) and Content Management API (`cma_token` secret).
- **Quirks**: the method controls both the sync parameter form and the stream list.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): depend on the connection method.
- Content Delivery API: none, pass `OBJECT_CONSTRUCT()`. The connection is already scoped to one space and environment.
- Content Management API:
  - `organization` (required): the Contentful organization ID, chosen from a dynamic list.
  - `space_pattern` (required, default `.*`): regex on space names. Only matching spaces are synced.
  - `environment_pattern` (required, default `.*`): regex on environment names. Only matching environments are synced.

**Streams**: a static list filtered by connection method (e.g. `entries`, `assets`, `content_types`). Content Delivery API connections get fewer streams.

## Notes

- Organization IDs can be listed with the plugin's `UDFS.FETCH_ORGANIZATIONS` function.
