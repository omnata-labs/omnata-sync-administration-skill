---
name: omnata-sync
description: "Manage, monitor and configure Omnata Sync Engine syncs (a Snowflake Native App). Use when the user asks about Omnata sync status, health, failed syncs, sync errors, run history, failed, stuck or delayed records, inbound data freshness, connections, or warehouse cost and credits; wants to troubleshoot a sync; wants CoCo to set up connections and inbound or outbound syncs end to end instead of the UI (including bulk streams from a file); wants to edit or re-authenticate a connection; asks where inbound data lands (storage location); wants branching, test vs production, or to copy config between branches; or wants to run, pause, delete or clean up syncs and connections. Triggers: omnata, sync status, sync failures, records not syncing, omnata cost, configure sync, create connection, CONFIGURE_OMNATA_INBOUND_SYNC, CONFIGURE_OMNATA_OUTBOUND_SYNC, BEGIN_CONNECTION_CREATION, storage location, sync branch, delete sync, first sync after installing a plugin."
license: Apache-2.0
---

# Omnata Sync Engine

This skill helps you monitor Omnata Sync Engine syncs running inside Snowflake, and make changes to them. Monitoring reads `OMNATA_SYNC_ENGINE.DATA_VIEWS`. Changes go through the app's `API` procedures: creating and editing connections; creating, configuring, running, pausing and deleting syncs; and record-level actions.

## Warnings

This skill can make changes that are costly, hard to reverse, or that send data outside Snowflake. It can:
- **Permanently delete** syncs, branches and connections. Deleting a sync also deletes its inbound raw tables and normalized views
- **Run syncs and full refreshes**, which use warehouse credits and the source app's API rate limits
- **Configure outbound syncs that change data in other apps.** Strategies such as Replace, Delete and Mirror overwrite or remove records in the destination, and outbound actions such as Jira `DELETE_ISSUES` and Zoho CRM `DELETE_RECORDS` delete records there
- **Send Snowflake data to third-party services** through outbound syncs
- **Create connections using credentials the user supplies** (API keys, tokens, service account keys, OAuth). The recommended route keeps secrets out of query history; see `references/configure-connections.md`
- **Change storage locations and privileges**: create schemas and database roles, transfer schema ownership and grant privileges to the app
- **Run a local Python script** (`scripts/render_storage_location.py`) that reads a plan file and prints a storage location preview
- **Fetch the public Snowflake and Omnata status pages** when preparing a support request

Before any of these, list what will be affected (names, IDs, and record or table counts where relevant) and wait for the user's explicit confirmation.

**End-to-end workflow:** install the Sync Engine and plugin (user), then create a connection (`references/configure-connections.md`), then create and run a sync (`references/configure-syncs.md`). When the user wants CoCo to set things up end to end instead of using the UI, start with the connection unless a suitable one exists, and carry on to the sync without waiting to be asked. Users can also add connections at any time later. If a sync is requested and no suitable connection exists, create the connection first.

## Routing

Identify what the user needs and read the appropriate reference file before proceeding:

| User intent | Reference file |
|---|---|
| Set up syncs end to end with CoCo instead of the UI, first setup after installing a plugin, sync data from or to an app with no connection yet, create or add a connection, edit a connection, rotate credentials, re-authorize OAuth, add credentials, OAuth or service account connection, BEGIN_CONNECTION_CREATION, BEGIN_CONNECTION_EDIT, COMPLETE_CONNECTION_CREATION, CANCEL_CONNECTION_CREATION | `references/configure-connections.md`, then `references/configure-syncs.md` |
| Delete a sync, clean up test syncs and connections, DELETE_SYNC | `references/actions.md` |
| Branching, test vs prod, dev and prod environments, sandbox connections, test a sync before it goes live, promote or copy config between branches, production or non-production connection, single-environment testing, SYNC_BRANCH | `references/branching.md` |
| Overall sync health, which syncs are failing | `references/monitoring-sync-status.md` |
| Outbound sync: run history, failed records, stuck records, error details | `references/monitoring-outbound.md` |
| Inbound sync: data freshness, run history, stream failures, cursor state, normalized views missing or stale, recreate views, refresh schema, access denied | `references/monitoring-inbound.md` |
| What connections exist, which are orphaned or problematic, connection health, test connection, delete connection, advanced connection management | `references/monitoring-connections.md` |
| Connection history, when was a connection created or edited, credential changes, secret updates | `references/monitoring-connections.md` |
| Contact Omnata support, raise a ticket, report a bug | `references/support-handoff.md` |
| Run, pause, resume, delete a sync; resync records; pre/post hooks; stored procedure reference; set storage location; reassign connection | `references/actions.md` |
| Create a new sync (connection must exist; plugin specifics in `references/plugins/<plugin_id>.md`), configure an outbound sync, configure an inbound sync, bulk add streams, configure Slack notifications, configure Salesforce sync, CONFIGURE_OMNATA_OUTBOUND_SYNC, CONFIGURE_OMNATA_INBOUND_SYNC | `references/configure-syncs.md` |
| Data management: choose where inbound data lands, design or preview a storage location template, set or change the default storage location, INBOUND_STORAGE_LOCATION, SET_DEFAULT_INBOUND_STORAGE_LOCATION | `references/data-management.md` |
| Deep diagnostic: stack traces, event logs, sync run lifecycle | `references/event-table-diagnostics.md` |
| Warehouse costs, credits, dollars, sync cost attribution, pricing, optimisation | `references/monitoring-warehouse-cost.md` |
| **Configure Syncs:** Configure an outbound sync, create a new outbound sync, create a sync to Slack/Salesforce/HubSpot, bulk-configure inbound sync streams, create sync with many streams, CONFIGURE_OMNATA_OUTBOUND_SYNC, CONFIGURE_OMNATA_INBOUND_SYNC | `references/configure-syncs.md` |
When troubleshooting a failed, incomplete, slow or timed-out sync run, one of the first checks
is whether the sync's warehouse was over capacity during the run. Queuing causes timeouts and
errors that look unrelated. See "Step 2b: Check Warehouse Capacity During the Run" in
`references/monitoring-sync-status.md`, and do it before working through the error text.

After surfacing any error message — whether from a failed outbound record (`LAST_RESULT`),
a failed inbound stream (`INBOUND_GLOBAL_ERROR_BY_STREAM`), or a sync run (`GLOBAL_ERROR`) —
always read `references/error-knowledge-base.md`, classify the error by origin
(Snowflake-side / Endpoint-side / Platform-level), and present the matching Omnata
remediation actions alongside your general knowledge interpretation of the destination
app's error.

If the error from `DATA_VIEWS` is insufficient to diagnose the root cause (e.g. a vague
`GLOBAL_ERROR`, an unexpected failure pattern, or the user asks "why" beyond what the error
text explains), escalate to `references/event-table-diagnostics.md` to query the Snowflake
Event Table for full stack traces and sync run lifecycle detail.

If a previously failing sync has recovered on its own and the cause is unclear, check the
connection's history for credential changes that coincide with the failure window —
see "Step 4: Connection History" in `references/monitoring-connections.md`. Consecutive
identical errors followed by self-recovery often indicate a credential rotation rather
than a transient platform outage.
## Key facts

- Database: `OMNATA_SYNC_ENGINE`, schema: `DATA_VIEWS`
- `SYNC_DIRECTION` values are lowercase: `'inbound'` or `'outbound'`
- All state columns (`HEALTH_STATE`, `RUN_STATE`, `APPLY_STATE`, `RECORD_STATE`) use `UPPER_UNDERSCORE` format
- JSON columns (`SYNC_SCHEDULE`, `LAST_RESULT`, `OUTBOUND_APPLY_STATE_COUNTS`) are accessed with Snowflake's `:` operator, e.g. `OUTBOUND_APPLY_STATE_COUNTS:SUCCESS::INTEGER`
- `PLUGIN_FQN` format: `PUBLISHER__APP_NAME`, e.g. `OMNATA__SALESFORCE`, `OMNATA_LABS__PAYPAL_BRAINTREE`
- Every sync has an implied `'main'` branch; branches only exist when `CONFIGURATION_MODE = 'advanced'`
- Most `API` procedures return an OBJECT. If a result shows `[object Object]`, read it with `SELECT TO_JSON($1) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))` straight after the call, before running anything else
