# Plugin reference pages

Per-plugin pages for connections and syncs. Each page follows `_TEMPLATE.md` and is built from `omnata-labs/plugin-*` source (`src/plugin.py` manifest and configuration forms) and `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/`. Where code and docs disagree, the page follows the code and notes the conflict under Sources.

`configure-connections.md` and `configure-syncs.md` keep the universal inbound and outbound procedure reference, and route plugin-specific detail to `references/plugins/<plugin_id>.md`.

Outbound rule: outbound syncs can only be created from the definition of an existing sync to the same plugin. The outbound sections describe what the parameters and mappings mean, so CoCo can adapt a copied definition, not build one from scratch. Building outbound config without a template was investigated and parked: the plugin form and target-field discovery procedures are not granted to customer roles, and the configure procedure does not validate plugin-specific config.

## Support matrix

| Page | Plugin | Inbound | Outbound strategies |
|---|---|---|---|
| `activecampaign.md` | ActiveCampaign | Yes | None |
| `aerobotics.md` | Aerobotics | Yes | None |
| `aircall.md` | Aircall | Yes | None |
| `airtable.md` | Airtable | Yes | Create, Update, Upsert, Replace |
| `bamboohr.md` | BambooHR | Yes | None |
| `claude.md` | Claude | Yes | None |
| `clockify.md` | Clockify | Yes | None |
| `confluence.md` | Confluence | Yes | None |
| `contentful.md` | Contentful | Yes | None |
| `databricks.md` | Databricks | Yes | None |
| `dynamics_365_business_central.md` | Microsoft Dynamics 365 Business Central | Yes | None |
| `dynamics_365_synapse_link.md` | Microsoft Dynamics 365 Synapse Link | Yes | None |
| `entra_id.md` | Microsoft Entra ID | Yes | None |
| `github.md` | Github | Yes | None |
| `google_ads.md` | Google Ads | Yes | Declared (Create, Upsert) but not implemented |
| `google_sheets.md` | Google Sheets | Yes | Replace |
| `hubspot.md` | Hubspot | Yes | Create, Upsert, Update, Delete |
| `infor_datalake.md` | Infor Datalake | Yes | None |
| `jira.md` | Jira | Yes | Create, Upsert |
| `linkedin_ads.md` | LinkedIn Ads | Yes | None (conversion events commented out) |
| `mailgun.md` | Mailgun | Yes | None |
| `marketo.md` | Marketo | No | Upsert, Update, Create |
| `meta_marketing.md` | Meta Marketing | Yes | None |
| `microsoft_ads.md` | Microsoft Ads (repo `plugin-bing-ads`) | Yes | None |
| `monday.md` | Monday.com | Yes | Create, Upsert, Mirror |
| `ms_excel.md` | MS Excel | Yes | Replace |
| `mssql.md` | Microsoft SQL Server | Yes | None |
| `mysql.md` | MySQL | Yes | None (commented out) |
| `netsuite.md` | NetSuite | Yes | None |
| `notion.md` | Notion | Yes | None |
| `paypal_braintree.md` | PayPal Braintree | Yes | None |
| `postgresql.md` | PostgreSQL | Yes | None |
| `questdb.md` | QuestDB | Yes | None |
| `reddit_ads.md` | Reddit Ads | Yes | None |
| `salesforce.md` | Salesforce | Yes | Create, Upsert, Update, Mirror, Delete, Record Merge |
| `sfmc.md` | Salesforce Marketing Cloud | Yes | Create, Upsert, Replace, Mirror |
| `shopify.md` | Shopify | Yes | Create, Upsert, Update, Delete |
| `slack.md` | Slack | Yes | Post Message |
| `typeform.md` | Typeform | Yes | None |
| `ukg_pro_wfm.md` | UKG Pro WFM | Yes | None |
| `wise.md` | Wise | Yes | None |
| `xero.md` | Xero | Yes | Create |
| `zendesk_support.md` | Zendesk Support | Yes | Create, Upsert, Mirror, Update, Delete |
| `zoho_crm.md` | Zoho CRM | Yes | Create, Update, Upsert |

## Repos with no implemented plugin

Stub pages only. Do not publish until the plugin exists.

| Page | Repo | Finding |
|---|---|---|
| `amazon-ads.md` | `plugin-amazon-ads` | Empty repo. Docs page says "Coming soon". |
| `azure-consumption.md` | `plugin-azure-consumption` | Unmodified plugin template. |
| `dynamics-365-ce.md` | `plugin-dynamics-365-ce` | No `src/`, one-line README. |
| `harvest.md` | `plugin-harvest` | Unmodified plugin template. |
| `tiktok-ads.md` | `plugin-tiktok-ads` | Unmodified plugin template. Docs page is a heading only. |

Excluded as scaffolding: `plugin-template`, `plugin-dev-automation`.

## Docs pages with no plugin repo in omnata-labs

Not drafted: `approvalmax`, `attio`, `bom-weather-data`, `mrpeasy`, `payhero`, `pinterest-ads`. These may be published from another org or not built yet.

## Open items before publishing

- **Plugin FQNs are derived, not confirmed.** Each is computed from `developer_id` and `plugin_id`. Several plugins use non-Omnata developer IDs (`MONITORIAL__MSSQL`, `MONITORIAL__POSTGRESQL`, `DATA_ENGINEERS__MONDAY`, `DATA_ENGINEERS__ENTRA_ID`, `OMNATA_LABS__PAYPAL_BRAINTREE`). Check them against `PLUGIN_FQN` in a live `DATA_VIEWS.CONNECTION`.
- **Multi-select and dropdown value formats are unconfirmed** for parameters such as `ad_accounts` (LinkedIn, Meta, Reddit), `workspaces` (Clockify), `companies` (Business Central), `schema` (MSSQL, Databricks), `workspace` (Typeform) and `profile_id` (Wise). The examples use the terse value form. Confirm against a UI-created sync's `SYNC_PARAMETERS`.
- **Docs conflicts to fix in the docs repo:**
  - Slack docs say `Create`, but the code registers `Post Message`.
  - Airtable docs say Incremental is supported, but the code is Full Refresh only.
  - SFMC and Google Sheets docs say Full Refresh only, but the code allows Incremental in some cases.
  - Contentful code has more streams, and a Content Delivery API method, than the docs list.
  - Xero docs list Payroll and Projects, but the code has only Accounting and Assets.
  - Google Ads docs describe a "Campaign Report Grouping" parameter that does not exist in code.
  - PayPal Braintree docs use `receivedDate` as the disputes cursor, but the code uses `received_date`.
- **Manifest and code mismatches:**
  - Google Ads declares outbound strategies, but the outbound code is empty stubs.
  - MSSQL has an outbound form but no outbound strategies.
