---
name: omnata-sync
description: "Manage, monitor, and configure Omnata Sync Engine syncs running as a Snowflake Native Application. Use when: user asks about Omnata sync status, sync health, failed syncs, sync errors, run history, stuck or delayed records, inbound data freshness, connection status, warehouse costs, sync cost attribution, cost in dollars, credit pricing, wants to investigate why a sync or record isn't working, wants to bulk-configure an inbound sync with many streams from a file or list, wants to configure an outbound sync, create a new outbound sync, or create a sync to a specific plugin, wants CoCo to set up syncs end to end instead of using the UI, wants to create a connection, or wants to delete a sync or clean up test syncs and connections. Triggers: omnata, sync status, sync health, sync failures, failed records, sync errors, sync run history, inbound sync, outbound sync, omnata connections, records not syncing, stuck records, omnata cost, omnata credits, warehouse cost, sync cost, omnata dollars, how much does omnata cost, omnata spend, omnata pricing, cost per sync, configure sync, bulk streams, create inbound sync, add streams from file, CONFIGURE_OMNATA_INBOUND_SYNC, CONFIGURE_OMNATA_OUTBOUND_SYNC, programmatic sync setup, configure an outbound sync, create a new outbound sync, create a sync to Slack, create a sync to Salesforce, create a sync to HubSpot, set up a sync end to end, do it without the UI, configure Omnata for me, I just installed the plugin, first sync, get my app data into Snowflake, create connection, set up connection, new connection, edit connection, rotate credentials, re-authenticate connection, add another connection, connect to an app, OAuth connection, service account connection, BEGIN_CONNECTION_CREATION, COMPLETE_CONNECTION_CREATION, delete sync, remove sync, clean up test syncs, delete connection, storage location, default storage location, INBOUND_STORAGE_LOCATION, which database does my data land in."
---

# Omnata Sync Engine

This skill helps you monitor and manage Omnata Sync Engine syncs running inside Snowflake. All data is read from `OMNATA_SYNC_ENGINE.DATA_VIEWS`.

**End-to-end workflow:** install the Sync Engine and plugin (user), then create a connection (`references/configure-connections.md`), then create and run a sync (`references/configure-syncs.md`). When the user wants CoCo to set things up end to end instead of using the UI, start with the connection unless a suitable one exists, and carry on to the sync without waiting to be asked. Users can also add connections at any time later. If a sync is requested and no suitable connection exists, create the connection first.

## Routing

Identify what the user needs and read the appropriate reference file before proceeding:

| User intent | Reference file |
|---|---|
| Set up syncs end to end with CoCo instead of the UI, first setup after installing a plugin, sync data from or to an app with no connection yet, create or add a connection, edit a connection, rotate credentials, re-authorize OAuth, add credentials, OAuth or service account connection, BEGIN_CONNECTION_CREATION, BEGIN_CONNECTION_EDIT, COMPLETE_CONNECTION_CREATION, CANCEL_CONNECTION_CREATION | `references/configure-connections.md`, then `references/configure-syncs.md` |
| Delete a sync, clean up test syncs and connections, DELETE_SYNC | `references/actions.md` |
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
