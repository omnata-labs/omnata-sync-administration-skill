<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
# Cortex Test Prompts — Monitoring Skills

Run each of these prompts in Cortex with the skill folder loaded to validate each monitoring workflow.
Use your NONPROD connection unless noted otherwise.

---

## 1. monitoring-sync-status

**Tests:** Overall health dashboard, failed sync investigation, summary counts

```
Check the health of all my Omnata syncs and give me a summary of what's failing or needs attention.
```

**What to verify:**
- Produces a grouped health table (HEALTHY / FAILED / INCOMPLETE / DELAYED / PENDING counts)
- Runs the Step 2 failed sync query and shows error details for CONTACTS to Airtable test, Jira Issues to Snowflake, google ads connector demo, DEV Sharepoint Company List Single File
- Flags paused syncs that have a snowflake_task schedule
- Ends with a formatted summary block

---

## 2. monitoring-outbound (run history)

**Tests:** Run history for a named outbound sync, trend analysis

```
Show me the last 20 runs for the CONTACTS to Chris Salesforce sync and tell me if there are any trends I should know about.
```

**What to verify:**
- Finds SYNC_ID 59 correctly
- Shows run table with DURATION_SECS, HEALTH_STATE, SUCCESS/FAIL counts extracted from OUTBOUND_APPLY_STATE_COUNTS JSON
- Notes that most runs were empty (0 records) and flags run 2531 as the one with activity
- Provides a trend summary

---

## 3. monitoring-outbound (failed records + error knowledge lookup)

**Tests:** Failed record list, error pattern grouping, knowledge base resolution steps

```
Which records are failing to sync in the CONTACTS to Airtable test sync? Show me what the errors look like and how to fix them.
```

**What to verify:**
- Finds SYNC_ID 23 (CONTACTS to Airtable test)
- Returns records with APPLY_STATE = DESTINATION_FAILURE
- Groups errors by LAST_RESULT in Step 4 to show the pattern across ~24,940 failed records
- Reads `error-knowledge-base.md` and classifies as Endpoint-side, matches the Airtable error type
- Presents resolution steps (not just the raw error)

**Alternative — Salesforce errors:**
```
Some of my contacts aren't syncing to Salesforce. What errors are they getting and what should I do about it?
```
- Should find CONTACTS to Chris Salesforce DESTINATION_FAILURE records (141 records)
- Should match the error pattern and classify as Endpoint-side (DESTINATION_FAILURE)
- Should recommend concrete steps, not just "check the error"

---

## 4. monitoring-outbound (single record lookup)

**Tests:** Looking up one specific record

```
In the CONTACTS to Chris Salesforce sync, can you look up the record for anna25@hotmail.com and tell me its current sync status?
```

**What to verify:**
- Runs Step 5 with IDENTIFIER = 'anna25@hotmail.com'
- Shows APP_IDENTIFIER (003cf00000UY63NAAT), APPLY_STATE (SUCCESS), TRANSFORMED_RECORD JSON
- Correctly reports it is successfully synced

---

## 5. monitoring-outbound (stuck records)

**Tests:** Cross-sync stuck record overview

```
Are there any records stuck or delayed across my Omnata syncs?
```

**What to verify:**
- Runs Step 6 across all syncs
- Surfaces ACCOUNTS to Salesforce Sandbox (10,002 RESYNC_REQUESTED records)
- Surfaces CONTACTS to Airtable test (24,940 DESTINATION_FAILURE with failure_count >= 3)
- Provides remediation recommendations table

---

## 6. monitoring-inbound (data freshness)

**Tests:** Inbound sync freshness overview and last run counts

```
How fresh is my inbound synced data? When did each of my inbound syncs last run?
```

**What to verify:**
- Filters to SYNC_DIRECTION = 'inbound' only (should return ~15 syncs)
- Shows HOURS_SINCE_SYNC for each
- Flags stale syncs (e.g. Jira Issues to Snowflake last ran 2024-05-30, google ads last ran 2025-07-14)
- Step 2 shows NEW/CHANGED/DELETED counts from last run
- Highlights any errored streams

---

## 7. monitoring-inbound (stream failures)

**Tests:** Stream failure identification, per-run stream error history, cursor state

```
Are any of my inbound sync streams failing? Show me what errors they're getting.
```

**What to verify:**
- Filters to `SYNC_DIRECTION = 'inbound'` and finds syncs where streams have errored
- Surfaces `INBOUND_GLOBAL_ERROR_BY_STREAM` JSON clearly per failed stream
- Step 3 shows error history across recent runs (persistent vs intermittent)
- Correctly explains the relationship between errored and abandoned streams
- Offers the diagnostic table matching error patterns to likely causes

**Alternative prompt (specific sync):**
```
The Jira Issues to Snowflake sync keeps failing. What stream errors is it getting and when did it last successfully sync?
```

**What to verify:**
- Finds SYNC_ID 16 (Jira Issues to Snowflake, HEALTH_STATE FAILED, last ran 2024-05-30)
- Shows Step 5 cursor state from INBOUND_LATEST_STREAMS_STATE
- Step 6 looks up SYNC_RECORD_STATE_HISTORY for the Jira stream to find last successful records

---

## 8. monitoring-connections

**Tests:** Connection health summary, orphaned connection detection

```
Give me an overview of all the Omnata connections and flag anything that looks problematic.
```

**What to verify:**
- Shows all connections grouped by production vs non-production
- Flags orphaned connections with no syncs (Dynamics Test Jade, James Airtable, James SQL Server, Meta-testing, Omnata monday dev, Mailgun James Test, marketo test, Zendesk Sandbox)
- Flags production connections with failed syncs (Airtable test → CONTACTS to Airtable test is FAILED; google ads connector demo → FAILED)
- Extracts APP cleanly from PLUGIN_FQN using SPLIT_PART

---

## 9. error-knowledge-base (error origin classification)

**Tests:** Origin-based error classification, SOURCE_FAILURE vs DESTINATION_FAILURE distinction

```
I have records failing in the CONTACTS to Airtable test sync with SOURCE_FAILURE state. What does this mean and how is it different from DESTINATION_FAILURE?
```

**What to verify:**
- Correctly distinguishes SOURCE_FAILURE (Snowflake-side, transform/mapping error) from DESTINATION_FAILURE (endpoint rejected the record)
- References TRANSFORMED_RECORD as the diagnostic tool to confirm origin
- Recommends Fix Source Data or Transform remediation actions from the knowledge base

---

## 10. event-table-diagnostics

**Tests:** Event table discovery, trace lookup, stack trace extraction

```
The Jira Issues to Snowflake sync is failing with a vague GLOBAL_ERROR. Can you look in the event table and give me the full stack trace?
```

**What to verify:**
- Runs Step 0 (SHOW PARAMETERS LIKE 'EVENT_TABLE') to discover event table location
- Runs Step 1 to discover the Omnata app name
- Finds trace for SYNC_ID 16 and extracts EXCEPTION_TYPE, EXCEPTION_MESSAGE, STACKTRACE
- Shows the lifecycle timeline (which phase the run failed at)
- Routes back to error-knowledge-base.md after extracting the error text

---

## 11. support-handoff

**Tests:** Status page checks, ticket preparation, support advisory

```
I've tried diagnosing this Salesforce sync failure but I'm stuck. Can you help me prepare a support ticket for Omnata?
```

**What to verify:**
- Runs SELECT CURRENT_REGION() to get Snowflake region
- Checks Snowflake status page for active incidents in the user's region
- Checks Omnata status page for active incidents
- Presents two-line platform status summary before the advisory
- Assembles ticket payload with SYNC_ID, SYNC_RUN_ID, PLUGIN_FQN, region, error text
- Provides email template for support@omnata.com with correct subject format
- Notes portal option at https://omnata.atlassian.net/servicedesk/customer/portal/1/group/1/create/1

---

## 12. monitoring-warehouse-cost

**Tests:** Warehouse discovery, per-sync cost attribution, optimisation recommendations

```
How much is Omnata costing me in Snowflake credits? Which syncs are the most expensive?
```

**What to verify:**
- Runs SHOW GRANTS TO APPLICATION OMNATA_SYNC_ENGINE to find granted warehouses
- Queries WAREHOUSE_METERING_HISTORY for credit totals
- Runs Step 2.5 to detect account edition and estimate $/credit
- Step 3 uses TASK_HISTORY → QUERY_HISTORY join to attribute costs per sync
- Ranks syncs by TOTAL_ELAPSED_SECS and provides dollar estimates
- Provides optimisation recommendations (warehouse sizing, queuing, schedule adjustments)
