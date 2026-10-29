---
name: omnata-monitoring-sync-status
description: "Check health and status of all Omnata Sync Engine syncs. Use when: user asks about Omnata sync status, sync health, failed syncs, sync errors, sync run history, or sync engine overview. Triggers: omnata sync status, omnata health, sync failures, sync errors, omnata sync engine status, omnata sync runs."
---

# Omnata Sync Status

Check the health, run state, and error details of all syncs in the Omnata Sync Engine.

## Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

## Workflow

### Step 1: Get Sync Overview

**Goal:** Retrieve all syncs with their current health, run state, and schedule.

**Execute:**

```sql
SELECT
    S.SYNC_ID,
    S.SYNC_SLUG,
    S.SYNC_NAME,
    S.SYNC_DIRECTION,
    S.RUN_STATE,
    S.HEALTH_STATE,
    SPLIT_PART(S.PLUGIN_FQN, '__', 2)      AS APP,
    S.CONFIGURATION_MODE,
    S.LATEST_RUN_START,
    S.SYNC_SCHEDULE:mode::VARCHAR           AS SCHEDULE_MODE,
    S.SYNC_SCHEDULE:sync_frequency_name::VARCHAR AS SCHEDULE_FREQUENCY
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
ORDER BY S.HEALTH_STATE, S.SYNC_NAME
```

**Present results as a summary table grouped by health state:**

| Health State | Meaning |
|---|---|
| `HEALTHY` | Operating normally |
| `FAILED` | All records in last run errored — needs investigation |
| `INCOMPLETE` | Last run had some successes but also some failures |
| `DELAYED` | Behind schedule due to rate limiting, otherwise healthy |
| `PENDING` | Configured but never run |

Also summarise by run state: `WAITING` (idle, scheduled), `PAUSED` (schedule suspended), `PENDING` (never run), `RUNNING` (currently active).

Flag notable issues:
- Any sync with `HEALTH_STATE = 'FAILED'`
- Any sync with `HEALTH_STATE = 'INCOMPLETE'`
- Any sync with `HEALTH_STATE = 'DELAYED'`
- Syncs with `RUN_STATE = 'PAUSED'` that have a `snowflake_task` schedule (paused but should be running)
- Syncs with `LATEST_RUN_START IS NULL` (never run)

### Step 2: Investigate Failed or Incomplete Syncs

**Goal:** For any syncs with `HEALTH_STATE IN ('FAILED', 'INCOMPLETE')`, retrieve error details from the most recent run.

**Execute:**

```sql
SELECT
    R.SYNC_RUN_ID,
    S.SYNC_SLUG,
    S.SYNC_NAME,
    SPLIT_PART(S.PLUGIN_FQN, '__', 2)  AS APP,
    S.HEALTH_STATE                      AS SYNC_HEALTH,
    S.RUN_STATE,
    S.LATEST_RUN_START,
    R.HEALTH_STATE                      AS RUN_HEALTH,
    R.RUN_START_DATETIME,
    R.RUN_END_DATETIME,
    DATEDIFF('second', R.RUN_START_DATETIME, R.RUN_END_DATETIME) AS DURATION_SECS,
    R.OUTBOUND_TOTAL_COUNT,
    R.OUTBOUND_APPLY_STATE_COUNTS:SUCCESS::INTEGER          AS OUT_SUCCESS,
    R.OUTBOUND_APPLY_STATE_COUNTS:DESTINATION_FAILURE::INTEGER AS OUT_DEST_FAIL,
    R.OUTBOUND_APPLY_STATE_COUNTS:SOURCE_FAILURE::INTEGER   AS OUT_SRC_FAIL,
    R.INBOUND_TOTAL_COUNT,
    R.INBOUND_ERRORED_STREAMS,
    R.GLOBAL_ERROR,
    R.INBOUND_GLOBAL_ERROR_BY_STREAM,
    R.CANCELLED_DATETIME
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON R.SYNC_ID = S.SYNC_ID
WHERE S.HEALTH_STATE IN ('FAILED', 'INCOMPLETE')
QUALIFY ROW_NUMBER() OVER (PARTITION BY R.SYNC_ID ORDER BY R.RUN_START_DATETIME DESC) = 1
ORDER BY S.SYNC_NAME
```

**For each problematic sync present:**
- Sync name, app, and when the last run started/ended
- Record counts: total processed, successes, failures
- The `GLOBAL_ERROR` message (catastrophic failure) if set
- Stream-level errors from `INBOUND_GLOBAL_ERROR_BY_STREAM` for inbound syncs
- Whether the run was cancelled (`CANCELLED_DATETIME IS NOT NULL`)

If no syncs are in `FAILED` or `INCOMPLETE` state, skip this step and report all syncs are healthy or pending.

### Step 2b: Check Warehouse Capacity During the Run

**Goal:** Before digging into the error text, rule out an overloaded warehouse. Do this for every failed, incomplete, slow or timed-out run from Step 2. An over-capacity warehouse makes sync queries queue, so runs slow down, hit `time_limit_mins` and fail with errors that look unrelated (timeouts, incomplete streams, expired tokens).

**1. Find the warehouse and run window.** The warehouse is in the sync's schedule:

```sql
SELECT S.SYNC_SLUG, S.SYNC_SCHEDULE:warehouse::VARCHAR AS WAREHOUSE,
       S.SYNC_SCHEDULE:time_limit_mins::INTEGER AS TIME_LIMIT_MINS,
       R.SYNC_RUN_ID, R.RUN_START_DATETIME, R.RUN_END_DATETIME,
       DATEDIFF('minute', R.RUN_START_DATETIME, R.RUN_END_DATETIME) AS DURATION_MINS
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON R.SYNC_ID = S.SYNC_ID
WHERE R.SYNC_RUN_ID = <sync_run_id>;
```

For a branch, take the warehouse from `DATA_VIEWS.SYNC_BRANCH.SYNC_SCHEDULE`. If the run has no end time, use the current time.

**2. Check queuing on that warehouse during the run.** Omnata's query tag carries no sync ID, so measure the warehouse over the run's time window. These `INFORMATION_SCHEMA` functions have no lag but only cover recent history (load: 14 days; queries: 7 days). For older runs, use the `SNOWFLAKE.ACCOUNT_USAGE` views of the same name.

```sql
-- Queries on the warehouse during the run
SELECT COUNT(*) AS QUERIES,
       ANY_VALUE(WAREHOUSE_SIZE) AS WAREHOUSE_SIZE,
       SUM(QUEUED_OVERLOAD_TIME) / 1000 AS QUEUED_OVERLOAD_SECS,
       MAX(QUEUED_OVERLOAD_TIME) / 1000 AS MAX_QUEUED_SECS,
       SUM(QUEUED_PROVISIONING_TIME) / 1000 AS PROVISIONING_SECS,
       SUM(EXECUTION_TIME) / 1000 AS EXECUTION_SECS
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE(
    WAREHOUSE_NAME => '<warehouse>',
    END_TIME_RANGE_START => '<run_start>'::TIMESTAMP_LTZ,
    END_TIME_RANGE_END => '<run_end>'::TIMESTAMP_LTZ,
    RESULT_LIMIT => 10000));

-- Warehouse load across the run
SELECT MAX(AVG_RUNNING) AS PEAK_RUNNING, MAX(AVG_QUEUED_LOAD) AS PEAK_QUEUED,
       AVG(AVG_QUEUED_LOAD) AS AVG_QUEUED, MAX(AVG_BLOCKED) AS PEAK_BLOCKED
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.WAREHOUSE_LOAD_HISTORY(
    DATE_RANGE_START => '<run_start>'::TIMESTAMP_LTZ,
    DATE_RANGE_END => '<run_end>'::TIMESTAMP_LTZ,
    WAREHOUSE_NAME => '<warehouse>'));
```

To see what else was using the warehouse, group the first query by `QUERY_TAG` (Omnata sync queries are tagged `RUN_SYNC Sync`; see `references/monitoring-warehouse-cost.md`) or by `USER_NAME`.

**3. Interpret:**
- **No overload queuing** (`QUEUED_OVERLOAD_SECS` near 0, `PEAK_QUEUED` 0): capacity isn't the cause. Carry on with the error text and `references/error-knowledge-base.md`.
- **Overload queuing** that's a noticeable share of the run, or `PEAK_QUEUED` above 0 for much of it: the warehouse was over capacity. Say so first, then offer the fixes:
  - Move this sync to a less busy warehouse, or give Omnata its own (`SET_SYNC_SCHEDULE`, see `references/actions.md`)
  - Stagger the schedules of syncs that share the warehouse
  - Make the warehouse multi-cluster, so queued queries get another cluster
  - Increase the size only for database connectors or heavy inbound syncs. Omnata recommends XS for API-based syncs, and queuing on API syncs is usually fixed by spreading the load rather than by a bigger warehouse
- **Duration close to `TIME_LIMIT_MINS`**: the run was likely cut off. If the warehouse was also queuing, fix capacity first. Otherwise suggest raising `time_limit_mins`.
- **High provisioning time** only: the warehouse was resuming or adding clusters. It's usually small; flag it only if it's a large share of the run.

Changing warehouses or schedules affects other workloads, so confirm with the user before changing anything.

### Step 3: Offer to Trigger a Re-Run (Optional)

**Goal:** For failed or incomplete syncs found in Step 2, assess whether a re-run would be useful and offer to trigger one.

**Triage each failed/incomplete sync using the Step 2 results.** Classify the error to determine whether re-running is appropriate.

**Do NOT suggest a re-run — a fix is required first:**

| Condition | How to detect from Step 2 | What to recommend instead |
|---|---|---|
| Transform / mapping errors | `OUT_SRC_FAIL > 0` (SOURCE_FAILURE records exist) | Fix field mapping or source data (see `error-knowledge-base.md` Section 3) |
| Auth / token expired | `GLOBAL_ERROR` contains "unauthorized", "token expired", "invalid session", "access token invalid", or HTTP 401 | Re-authenticate the connection in the Omnata UI |
| Permission denied | `GLOBAL_ERROR` contains "forbidden", "insufficient access", "not permitted", or HTTP 403 | Fix permissions in the destination app |
| Data validation errors | `OUT_DEST_FAIL > 0` AND `GLOBAL_ERROR` or error pattern references field validation, required fields, or HTTP 422 | Fix field mapping or source data values |
| Sync is paused | `RUN_STATE = 'PAUSED'` | Use `CALL OMNATA_SYNC_ENGINE.API.RESUME_SYNC('<sync_slug>', 'main')` first |

For these cases, explain what needs fixing and route to the appropriate remediation in `error-knowledge-base.md`. Do not offer a re-run.

**DO suggest a re-run — likely to succeed or gain diagnostic information:**

| Condition | How to detect from Step 2 |
|---|---|
| Transient / server errors | `GLOBAL_ERROR` contains "service unavailable", "internal server error", "bad gateway", "timeout", "rate limit", "throttle", or HTTP 500/502/503/429 |
| Vague `GLOBAL_ERROR` | `GLOBAL_ERROR IS NOT NULL` but text doesn't match any of the "do not re-run" patterns above — a fresh run produces a new event table trace for deeper diagnosis |
| `INCOMPLETE` state | `SYNC_HEALTH = 'INCOMPLETE'` — the run was interrupted, not a hard failure |
| Network / connectivity (possibly transient) | `GLOBAL_ERROR` contains "connection refused", "DNS", "SSL", "certificate" — worth one retry before escalating |
| Stale failure | `LATEST_RUN_START` is more than 24 hours ago — the underlying issue may have been resolved externally |

**Before offering a re-run for transient or network errors: check the consecutive failure depth.**

If any sync matched the "Transient / server errors", "Vague `GLOBAL_ERROR`", or "Network / connectivity" rows above, run the following to determine whether the error is genuinely one-off or has persisted across multiple runs. This applies equally to inbound and outbound syncs — `GLOBAL_ERROR` is set at the run level, indicating the sync could not start or complete, not a record-level failure.

```sql
SELECT
    R.SYNC_RUN_ID,
    R.RUN_START_DATETIME,
    R.HEALTH_STATE                              AS RUN_HEALTH,
    R.CANCELLED_DATETIME IS NOT NULL            AS WAS_CANCELLED,
    CASE WHEN R.GLOBAL_ERROR IS NOT NULL
         THEN LEFT(R.GLOBAL_ERROR, 150)
    END                                         AS GLOBAL_ERROR_EXCERPT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
WHERE R.SYNC_ID = <sync_id>
ORDER BY R.RUN_START_DATETIME DESC
LIMIT 15
```

Working from the most recent run backward, count how many consecutive runs have a non-null `GLOBAL_ERROR` before reaching the first `HEALTHY` run — this is the **consecutive failure streak**.

| Streak result | Action |
|---|---|
| Streak = 1 or 2 runs | Likely genuinely transient — proceed to the re-run offer below |
| Streak ≥ 3 runs, errors consistent (same or similar text) | Not genuinely transient — investigate before re-running. Three paths to check in parallel: (1) **Status pages** — check `https://status.snowflake.com` and `https://status.omnata.com` for active incidents that explain the sustained failure (see `references/support-handoff.md` Step 1); (2) **Error origin** — read `references/error-knowledge-base.md` to classify whether this is endpoint-side (sustained outage or auth issue), platform-level (networking, EAI), or Snowflake-side; (3) **Connection history** — check `references/monitoring-connections.md` Step 4 for credential changes that coincide with the failure window. Only offer a re-run once one of these paths has identified and resolved the root cause. |
| Streak ≥ 3 runs, errors varied (different text across runs) | Mixed failure pattern — proceed to re-run but flag to the user that the sync has been failing repeatedly and they should monitor the result closely |
| All recent runs are `INCOMPLETE` with no `GLOBAL_ERROR` | Run was interrupted before completing, not erroring at the platform level — proceed to re-run offer |

**Ask the user before triggering.** Present the re-runnable syncs and ask which (if any) they'd like to trigger. Do not trigger automatically.

**Execute the re-run** (for full parameter reference, see `references/actions.md` — Sync Lifecycle):

```sql
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(
    NULL,                                -- SYNC_ID (null when using slug)
    '<sync_slug>',                       -- SYNC_SLUG from DATA_VIEWS.SYNC
    'main',                              -- BRANCH_NAME
    'external',                          -- RUN_SOURCE_NAME
    {'triggered_by': 'cortex_code'},     -- RUN_SOURCE_METADATA
    false                                -- WAIT_FOR_COMPLETION (async)
);
```

**After triggering:**

1. Check the returned OBJECT — it confirms whether the run was successfully enqueued
2. Query for the new run:
   ```sql
   SELECT SYNC_RUN_ID, RUN_STATE, HEALTH_STATE, RUN_START_DATETIME
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN
   WHERE SYNC_ID = (SELECT SYNC_ID FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_SLUG = '<sync_slug>')
   ORDER BY RUN_START_DATETIME DESC
   LIMIT 1
   ```
3. Report the new run ID and its initial state to the user
4. If the user wants to monitor the run, suggest checking back shortly or using `monitoring-outbound.md` / `monitoring-inbound.md` to review the run once it completes

### Step 4: Summary

**Present a final summary:**

```
Omnata Sync Engine Status
=========================
Total syncs:    <count>
  Healthy:      <count>
  Failed:       <count>
  Incomplete:   <count>
  Delayed:      <count>
  Pending:      <count>

Run States:
  Waiting:      <count>
  Running:      <count>
  Paused:       <count>
  Pending:      <count>
```

If failures or incomplete syncs exist, summarise the errors found in Step 2 and whether any re-runs were triggered in Step 3. Recommend next steps (investigate failed records, check connection credentials, review error messages, or monitor re-triggered runs).

## Stopping Points

- After Step 1 if the user only wanted a quick overview
- After Step 2 if the user wants to take action on specific failures before continuing
- After Step 3 if the user triggered a re-run and wants to wait for results before continuing
- After Step 4 for the full summary with recommendations
