# TikTok Ads (incomplete, template code only)

| | |
|---|---|
| Plugin ID | `template_app` (manifest value; repo is `plugin-tiktok-ads`) |
| Plugin FQN | Unknown. The manifest would give `MY_COMPANY__TEMPLATE_APP`, which is not a real published plugin. |
| Directions | Not determinable. The template manifest declares inbound and Create/Update outbound, but none of it is TikTok-specific. |
| Docs | `apps/tiktok-ads/README.md` (title only, no content) |

## Status

The repository does not yet contain a real TikTok Ads plugin. `src/plugin.py` is the unmodified Omnata plugin template:

- `get_manifest()` returns `plugin_id="template_app"`, `plugin_name="TemplateApp"`, `developer_id="my_company"`.
- `connection_form()` is a generic "API Key" method.
- `outbound_configuration_form()` offers placeholder `target_object` values (Lead, Contact, Account).
- `inbound_stream_list()` returns placeholder streams `leads`, `contacts` and custom objects from a `tenant_url` API.

Do not use this page to configure syncs. Revisit once the plugin is implemented.

## Sources

- Code: `omnata-labs/plugin-tiktok-ads` at `src/plugin.py` (template scaffold)
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/tiktok-ads/README.md` contains only a heading
- Not verified: real plugin_id, FQN, streams, parameters or strategies for TikTok Ads.
