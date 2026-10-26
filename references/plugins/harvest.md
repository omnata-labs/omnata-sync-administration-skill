# Harvest

Not a real plugin yet. The `plugin-harvest` repo contains the unmodified Omnata plugin template, so no Harvest-specific sync configuration can be documented.

## What was found

- `src/plugin.py` has a `get_manifest()`, but it returns template placeholder values: `plugin_id="template_app"`, `plugin_name="TemplateApp"`, `developer_id="my_company"`, `docs_url="https://docs.mycompany.com"`.
- The manifest declares inbound support and `Create` / `Update` outbound strategies, but the code is the generic template: an `api_key` connection field, a `target_object` outbound parameter, and example streams `leads`, `contacts` plus custom objects read from a placeholder API. None of this calls the Harvest API.
- The repo `README.md` is the template's ("A template repo for an Omnata Plugin").
- `src/` has no `__init__.py`, no `tier.txt` and no schemas, unlike released plugins.

## Guidance

Do not configure Harvest syncs from this page. If a Harvest connection exists in an account, check its real plugin via `DATA_VIEWS.CONNECTION.PLUGIN_FQN` and copy parameters from a UI-created sync instead.

## Sources

- Docs: none. There is no Harvest folder under `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/`.
- Plugin ID, FQN, parameters and streams could not be verified because the code is template-only. File named after the repo.
