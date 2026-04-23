<!-- owner: shared — both cortex-code and co-work may edit this file. Respect section ownership markers. Only append new routing rows or sections. Do not rewrite content owned by the other tool. -->
---
name: omnata-sync
description: "Manage and monitor Omnata Sync Engine syncs running as a Snowflake Native Application. Use when: user asks about Omnata sync status, sync health, failed syncs, sync errors, run history, stuck or delayed records, inbound data freshness, connection status, warehouse costs, sync cost attribution, cost in dollars, credit pricing, or wants to investigate why a sync or record isn't working. Triggers: omnata, sync status, sync health, sync failures, failed records, sync errors, sync run history, inbound sync, outbound sync, omnata connections, records not syncing, stuck records, omnata cost, omnata credits, warehouse cost, sync cost, omnata dollars, how much does omnata cost, omnata spend, omnata pricing, cost per sync."
---

# Omnata Sync Engine

This skill helps you monitor and manage Omnata Sync Engine syncs running inside Snowflake. All data is read from `OMNATA_SYNC_ENGINE.DATA_VIEWS`.

## Routing

Identify what the user needs and read the appropriate reference file before proceeding:

| User intent | Reference file |
|---|---|
<!-- section-owner: co-work — monitoring workflow routes -->
| Overall sync health, which syncs are failing | `references/monitoring-sync-status.md` |
| Outbound sync: run history, failed records, stuck records, error details | `references/monitoring-outbound.md` |
| Inbound sync: data freshness, run history, stream failures, cursor state | `references/monitoring-inbound.md` |
| What connections exist, which are orphaned or problematic, connection health, test connection, delete connection, advanced connection management | `references/monitoring-connections.md` |
| Connection history, when was a connection created or edited, credential changes, secret updates | `references/monitoring-connections.md` |
| Contact Omnata support, raise a ticket, report a bug | `references/support-handoff.md` |
<!-- end-section-owner: co-work -->
<!-- section-owner: cortex-code — diagnostic and error classification routes -->
| Deep diagnostic: stack traces, event logs, sync run lifecycle | `references/event-table-diagnostics.md` |
| Warehouse costs, credits, dollars, sync cost attribution, pricing, optimisation | `references/monitoring-warehouse-cost.md` |
<!-- end-section-owner: cortex-code -->

<!-- section-owner: cortex-code — error classification and escalation instructions -->
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
<!-- end-section-owner: cortex-code -->

<!-- section-owner: co-work — key facts -->
## Key facts

- Database: `OMNATA_SYNC_ENGINE`, schema: `DATA_VIEWS`
- `SYNC_DIRECTION` values are lowercase: `'inbound'` or `'outbound'`
- All state columns (`HEALTH_STATE`, `RUN_STATE`, `APPLY_STATE`, `RECORD_STATE`) use `UPPER_UNDERSCORE` format
- JSON columns (`SYNC_SCHEDULE`, `LAST_RESULT`, `OUTBOUND_APPLY_STATE_COUNTS`) are accessed with Snowflake's `:` operator, e.g. `OUTBOUND_APPLY_STATE_COUNTS:SUCCESS::INTEGER`
- `PLUGIN_FQN` format: `PUBLISHER__APP_NAME`, e.g. `OMNATA__SALESFORCE`, `OMNATA_LABS__PAYPAL_BRAINTREE`
- Every sync has an implied `'main'` branch; branches only exist when `CONFIGURATION_MODE = 'advanced'`
<!-- end-section-owner: co-work -->
