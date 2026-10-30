# Plugin reference pages

Per-plugin pages for connections and syncs. Each page follows `_TEMPLATE.md` and holds only what the installed apps don't expose: sync parameter meanings, gotchas, required approaches and warnings. Point users to the plugin's `DOCS_URL` for explanations and setup.

`configure-connections.md` and `configure-syncs.md` keep the universal inbound and outbound procedure reference, and route plugin-specific detail to `references/plugins/<plugin_id>.md`.

Outbound rule: outbound syncs can only be created from the definition of an existing sync to the same plugin. The outbound sections describe what the parameters and mappings mean, so CoCo can adapt a copied definition, not build one from scratch. Building outbound config without a template was investigated and parked: the plugin form and target-field discovery procedures are not granted to customer roles, and the configure procedure does not validate plugin-specific config.

## Pages

Directions and outbound strategies aren't listed here. Look them up in `DATA_VIEWS.PLUGIN` ("Plugin capabilities come from the installed apps" in `configure-syncs.md`).

| Page | Plugin |
|---|---|
| `activecampaign.md` | ActiveCampaign |
| `aerobotics.md` | Aerobotics |
| `aircall.md` | Aircall |
| `airtable.md` | Airtable |
| `bamboohr.md` | BambooHR |
| `claude.md` | Claude |
| `clockify.md` | Clockify |
| `confluence.md` | Confluence |
| `contentful.md` | Contentful |
| `databricks.md` | Databricks |
| `dynamics_365_business_central.md` | Microsoft Dynamics 365 Business Central |
| `dynamics_365_synapse_link.md` | Microsoft Dynamics 365 Synapse Link |
| `entra_id.md` | Microsoft Entra ID |
| `github.md` | GitHub |
| `google_ads.md` | Google Ads |
| `google_sheets.md` | Google Sheets |
| `hubspot.md` | Hubspot |
| `infor_datalake.md` | Infor Datalake |
| `jira.md` | Jira |
| `linkedin_ads.md` | LinkedIn Ads |
| `mailgun.md` | Mailgun |
| `marketo.md` | Marketo |
| `meta_marketing.md` | Meta Marketing |
| `microsoft_ads.md` | Microsoft Ads (repo `plugin-bing-ads`) |
| `monday.md` | Monday.com |
| `ms_excel.md` | MS Excel |
| `mssql.md` | Microsoft SQL Server |
| `mysql.md` | MySQL |
| `netsuite.md` | NetSuite |
| `notion.md` | Notion |
| `paypal_braintree.md` | PayPal Braintree |
| `postgresql.md` | PostgreSQL |
| `questdb.md` | QuestDB |
| `reddit_ads.md` | Reddit Ads |
| `salesforce.md` | Salesforce |
| `sfmc.md` | Salesforce Marketing Cloud |
| `shopify.md` | Shopify |
| `slack.md` | Slack |
| `typeform.md` | Typeform |
| `ukg_pro_wfm.md` | UKG Pro WFM |
| `wise.md` | Wise |
| `xero.md` | Xero |
| `zendesk_support.md` | Zendesk Support |
| `zoho_crm.md` | Zoho CRM |

## No released plugin

Stub pages only: `amazon-ads.md`, `azure-consumption.md`, `dynamics-365-ce.md`, `harvest.md`, `tiktok-ads.md`. Do not configure syncs from them.

## No reference page yet

`approvalmax`, `attio`, `bom-weather-data`, `mrpeasy`, `payhero`, `pinterest-ads`. Copy parameters from a UI-created sync instead.
