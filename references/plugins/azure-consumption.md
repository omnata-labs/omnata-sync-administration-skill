# Azure Consumption (incomplete, template code only)

| | |
|---|---|
| Plugin ID | `template_app` (manifest value; repo is `plugin-azure-consumption`) |
| Plugin FQN | Unknown. The manifest would give `MY_COMPANY__TEMPLATE_APP`, which is not a real published plugin. |
| Directions | Not determinable. The template manifest declares inbound and Create/Update outbound, but none of it is Azure-specific. |
| Docs | None. No `apps/` folder for Azure Consumption. |

## Status

The repository does not yet contain a real Azure Consumption plugin. `src/plugin.py` is the unmodified Omnata plugin template (`plugin_id="template_app"`, `plugin_name="TemplateApp"`, `developer_id="my_company"`), and `inbound_stream_list()` returns no Azure streams.

Do not use this page to configure syncs. Revisit once the plugin is implemented.

## Sources

- Code: `omnata-labs/plugin-azure-consumption` at `src/plugin.py` (template scaffold)
- Docs: none found
- Not verified: real plugin_id, FQN, streams, parameters or strategies for Azure Consumption.
