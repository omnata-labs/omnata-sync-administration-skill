<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
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

### Step 3: Offer to Trigger a Re-Run (Optional)

<!-- contributor: cortex-code — RUN_SYNC procedure integration and triage logic -->

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

**Ask the user before triggering.** Present the re-runnable syncs and ask which (if any) they'd like to trigger. Do not trigger automatically.

**Execute the re-run:**

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

Notes on `RUN_SYNC` parameters:
- Use `SYNC_SLUG` (from `DATA_VIEWS.SYNC`) rather than `SYNC_ID` — it's human-readable and unambiguous
- Set `SYNC_ID` to `NULL` when using `SYNC_SLUG` (they are mutually exclusive)
- `BRANCH_NAME` = `'main'` for the primary sync; use the branch name if the user specifies a branch
- `WAIT_FOR_COMPLETION = false` returns immediately after enqueuing — the sync runs asynchronously via a Snowflake task
- `RUN_SOURCE_METADATA` tags this run as triggered by Cortex Code for traceability in run history

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
