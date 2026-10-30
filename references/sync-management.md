---
name: omnata-sync-management
description: "Monitor, diagnose and act on Omnata Sync Engine syncs, inbound and outbound. Covers sync health and failed runs, warehouse load and credits during runs (read-only INFORMATION_SCHEMA queries), inbound freshness, stream failures, cursor state and normalized view repair, outbound failed, stuck and delayed records, and pre/post run hooks. Can change things, always after the user confirms: run, pause, resume, rename, reschedule or delete syncs (RUN_SYNC, RESUME_SYNC, DELETE_SYNC), refresh inbound schemas and recreate views, mark streams for full refresh, move inbound tables, resync or skip outbound records, and, only on Omnata support instruction, set app settings or cursor state (SET_APP_SETTING, SET_INBOUND_SYNC_STATE). Use when: user asks about Omnata sync status, health or failures; or wants to run, pause, resume, re-run, delete, full-refresh or resync an Omnata sync. Triggers: omnata sync status, omnata sync failures, omnata inbound sync, delete omnata sync, RUN_SYNC, RESUME_SYNC, DELETE_SYNC."
---

# Omnata Sync Management

Monitor and diagnose Omnata syncs, then act on them. Part 1 covers every sync; Parts 2 and 3 go deeper into inbound and outbound syncs; Parts 4 to 6 cover sync-level actions. To create or reconfigure a sync, use `references/configure-syncs.md`. For connections, use `references/connection-management.md`.

## Changes this reference can make

Most of this reference only reads `OMNATA_SYNC_ENGINE.DATA_VIEWS`. These steps change things, and each one needs the user's confirmation first:
- **Runs and schedules:** run, re-run, pause, resume, rename, reschedule or set an owner on a sync. Runs use warehouse credits and the source app's API rate limits; outbound runs write to the destination app
- **Deletes:** delete a sync. Irreversible; inbound syncs lose their raw tables and normalized views
- **Inbound data:** refresh stream schemas, recreate normalized views, mark streams (or a whole plugin) for full refresh, move a sync's tables, drop orphaned inbound objects
- **Outbound records:** resync, skip or mark records as successful, one by one or in bulk
- **Hooks:** create pre/post run hook procedures that run for every sync

## Part 1: All syncs: status and triage

Check the health, run state, and error details of all syncs in the Omnata Sync Engine.

### Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

### Workflow

#### Step 1: Get Sync Overview

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
- Syncs with `RUN_STATE = 'PAUSED'` that have a `snowflake_task` schedule (paused with a schedule: ask the user whether that's intended)
- Syncs with `LATEST_RUN_START IS NULL` (never run)

#### Step 2: Investigate Failed or Incomplete Syncs

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

#### Step 2b: Check Warehouse Capacity During the Run, and Suggest Fixes

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
  - Move this sync to a less busy warehouse, or give Omnata its own (`SET_SYNC_SCHEDULE`, see Part 4, "Rename, Reschedule or Assign an Owner")
  - Stagger the schedules of syncs that share the warehouse
  - Make the warehouse multi-cluster, so queued queries get another cluster
  - Increase the size only for database connectors or heavy inbound syncs. Omnata recommends XS for API-based syncs, and queuing on API syncs is usually fixed by spreading the load rather than by a bigger warehouse
- **Duration close to `TIME_LIMIT_MINS`**: the run was likely cut off. If the warehouse was also queuing, fix capacity first. Otherwise suggest raising `time_limit_mins`.
- **High provisioning time** only: the warehouse was resuming or adding clusters. It's usually small; flag it only if it's a large share of the run.

Changing warehouses or schedules affects other workloads, so confirm with the user before changing anything.

#### Step 3: Offer to Trigger a Re-Run (Optional)

**Goal:** For failed or incomplete syncs found in Step 2, assess whether a re-run would be useful and offer to trigger one.

**Triage each failed/incomplete sync using the Step 2 results.** Classify the error to determine whether re-running is appropriate.

**Do NOT suggest a re-run — a fix is required first:**

| Condition | How to detect from Step 2 | What to recommend instead |
|---|---|---|
| Transform / mapping errors | `OUT_SRC_FAIL > 0` (SOURCE_FAILURE records exist) | Fix field mapping or source data (see `error-knowledge-base.md` Section 3) |
| Auth / token expired | `GLOBAL_ERROR` contains "unauthorized", "token expired", "invalid session", "access token invalid", or HTTP 401 | Re-authenticate the connection in the Omnata UI |
| Permission denied | `GLOBAL_ERROR` contains "forbidden", "insufficient access", "not permitted", or HTTP 403 | Fix permissions in the destination app |
| Data validation errors | `OUT_DEST_FAIL > 0` AND `GLOBAL_ERROR` or error pattern references field validation, required fields, or HTTP 422 | Fix field mapping or source data values |
| Sync is paused | `RUN_STATE = 'PAUSED'` | Ask the user why it was paused first; it may have been paused on purpose. Resume only if they confirm: `CALL OMNATA_SYNC_ENGINE.API.RESUME_SYNC('<sync_slug>', 'main')` |

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
| Streak ≥ 3 runs, errors consistent (same or similar text) | Not genuinely transient — investigate before re-running. Three paths to check in parallel: (1) **Status pages** — check `https://status.snowflake.com` and `https://status.omnata.com` for active incidents that explain the sustained failure (see `references/support-handoff.md` Step 1); (2) **Error origin** — read `references/error-knowledge-base.md` to classify whether this is endpoint-side (sustained outage or auth issue), platform-level (networking, EAI), or Snowflake-side; (3) **Connection history** — check `references/connection-management.md` Step 4 for credential changes that coincide with the failure window. Only offer a re-run once one of these paths has identified and resolved the root cause. |
| Streak ≥ 3 runs, errors varied (different text across runs) | Mixed failure pattern — proceed to re-run but flag to the user that the sync has been failing repeatedly and they should monitor the result closely |
| All recent runs are `INCOMPLETE` with no `GLOBAL_ERROR` | Run was interrupted before completing, not erroring at the platform level — proceed to re-run offer |

**Ask the user before triggering.** Present the re-runnable syncs and ask which (if any) they'd like to trigger. Do not trigger automatically.

**Execute the re-run** (for the full parameter reference, see Part 4, "Run a Sync"). A run uses warehouse credits and the source app's API rate limits, and outbound runs write to the destination app. Only run it after the user agrees:

**Before running:** a run uses warehouse credits and the source app's API rate limits, and outbound runs write to the destination app. Get the user's confirmation.

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
4. If the user wants to monitor the run, suggest checking back shortly or using Part 3 (outbound) or Part 2 (inbound) to review the run once it completes

#### Step 4: Summary

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

### Stopping Points

- After Step 1 if the user only wanted a quick overview
- After Step 2 if the user wants to take action on specific failures before continuing
- After Step 3 if the user triggered a re-run and wants to wait for results before continuing
- After Step 4 for the full summary with recommendations

## Part 2: Inbound syncs

Investigate inbound syncs — those that pull data from an external application into Snowflake.
Covers data freshness, run history, stream-level failures, cursor state, and error diagnosis.

### Background

Inbound syncs pull records from an external app and land them in Snowflake. Each object type
(e.g. Account, Contact, Order) is a **stream**. Unlike outbound syncs — where failures are
tracked per record — inbound failures occur at the **stream level**. There is no per-record
error table for inbound syncs. Errors are captured in the `SYNC_RUN` table per run, and
the current cursor state (how far the stream has synced) is stored in the `SYNC` table.

A stream can end a run in these states:

| Stream state | Meaning |
|---|---|
| **Successful** | Completed — all records processed |
| **Errored** | Encountered an error and stopped mid-run |
| **Abandoned** | Skipped — another stream's failure caused early exit |
| **Cancelled** | Run hit its time limit before this stream completed |

Key columns on `SYNC_RUN` for inbound syncs:

| Column | Meaning |
|---|---|
| `INBOUND_TOTAL_COUNT` | Total records retrieved this run |
| `INBOUND_NEW_COUNT` | New records inserted into Snowflake |
| `INBOUND_CHANGED_COUNT` | Records updated in Snowflake |
| `INBOUND_DELETED_COUNT` | Records deleted from Snowflake |
| `INBOUND_ERRORED_STREAMS` | Array of stream names that errored |
| `INBOUND_ABANDONED_STREAMS` | Array of stream names that were abandoned |
| `INBOUND_CANCELLED_STREAMS` | Array of stream names cut off by time limit |
| `INBOUND_SUCCESSFUL_STREAMS` | Array of stream names that completed successfully |
| `INBOUND_GLOBAL_ERROR_BY_STREAM` | JSON object: stream name → error message |
| `GLOBAL_ERROR` | Catastrophic run-level error (set when the run failed before streams started) |

### Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

---

### Workflow

#### Step 1: Inbound Sync Overview

**Goal:** List all inbound syncs with their health state, last run time, and schedule — to
identify syncs that are failing, paused, or overdue.

```sql
SELECT
    S.SYNC_ID,
    S.SYNC_NAME,
    SPLIT_PART(S.PLUGIN_FQN, '__', 2)           AS APP,
    S.HEALTH_STATE,
    S.RUN_STATE,
    S.LATEST_RUN_START,
    DATEDIFF('hour', S.LATEST_RUN_START, CURRENT_TIMESTAMP()) AS HOURS_SINCE_SYNC,
    S.SYNC_SCHEDULE:mode::VARCHAR                AS SCHEDULE_MODE,
    S.SYNC_SCHEDULE:sync_frequency_name::VARCHAR AS SCHEDULE_FREQUENCY
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
WHERE S.SYNC_DIRECTION = 'inbound'
ORDER BY S.HEALTH_STATE, S.LATEST_RUN_START DESC NULLS LAST
```

Highlight:
- Syncs where `LATEST_RUN_START IS NULL` — never run
- Syncs where `HEALTH_STATE` is not `HEALTHY`
- Syncs that appear stale: scheduled syncs where `HOURS_SINCE_SYNC` significantly exceeds
  their frequency (e.g. a daily sync that hasn't run in 36+ hours)
- Syncs with `RUN_STATE = 'PAUSED'` that have a schedule (ask whether the pause is intended)

If the user named a specific sync, find its `SYNC_ID`:

```sql
SELECT
    SYNC_ID,
    SYNC_NAME,
    SYNC_SLUG,
    HEALTH_STATE,
    RUN_STATE,
    LATEST_RUN_START,
    SPLIT_PART(PLUGIN_FQN, '__', 2) AS APP
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_DIRECTION = 'inbound'
  AND (SYNC_NAME ILIKE '%<user_provided_name>%'
       OR SYNC_SLUG ILIKE '%<user_provided_name>%')
ORDER BY SYNC_NAME
```

Ask the user to confirm which sync to investigate if multiple are returned.

---

#### Step 2: Run History

**Goal:** Show recent runs with durations, record counts, and stream failure breakdown.

```sql
SELECT
    R.SYNC_RUN_ID,
    R.RUN_START_DATETIME,
    R.RUN_END_DATETIME,
    DATEDIFF('second', R.RUN_START_DATETIME, R.RUN_END_DATETIME) AS DURATION_SECS,
    R.HEALTH_STATE,
    R.CANCELLED_DATETIME IS NOT NULL         AS WAS_CANCELLED,
    R.INBOUND_TOTAL_COUNT,
    R.INBOUND_NEW_COUNT,
    R.INBOUND_CHANGED_COUNT,
    R.INBOUND_DELETED_COUNT,
    R.INBOUND_ERRORED_STREAMS,
    R.INBOUND_ABANDONED_STREAMS,
    R.INBOUND_CANCELLED_STREAMS,
    R.INBOUND_SUCCESSFUL_STREAMS,
    R.GLOBAL_ERROR,
    R.INBOUND_GLOBAL_ERROR_BY_STREAM
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
WHERE R.SYNC_ID = <sync_id>
  AND R.INBOUND_TOTAL_COUNT IS NOT NULL  -- exclude runs that did not execute inbound logic
ORDER BY R.RUN_START_DATETIME DESC
LIMIT 20
```

Present as a table, most-recent first. Format `DURATION_SECS` as `Xm Ys`. Flag:
- Runs where `HEALTH_STATE != 'HEALTHY'`
- Cancelled runs (`WAS_CANCELLED = TRUE`)
- Runs with zero records processed (empty runs — normal but worth noting if unexpected)
- Consecutive failures

After the table, summarise the trend:
- Success rate across shown runs
- Average duration (exclude cancelled)
- Whether `INBOUND_NEW_COUNT` / `INBOUND_CHANGED_COUNT` volumes are growing, stable, or dropping
- Whether the same streams appear in `INBOUND_ERRORED_STREAMS` across multiple runs
  (persistent failure vs one-off)
- Surface any `GLOBAL_ERROR` values and offer to investigate further

---

#### Step 3: Stream Failure Detail

**Goal:** For syncs with stream errors — identify which streams failed, what the errors are,
and whether failures are persistent or intermittent.

**Find all inbound syncs with stream failures (cross-sync view):**

```sql
SELECT
    S.SYNC_ID,
    S.SYNC_NAME,
    SPLIT_PART(S.PLUGIN_FQN, '__', 2)    AS APP,
    S.HEALTH_STATE,
    R.SYNC_RUN_ID,
    R.HEALTH_STATE                        AS LAST_RUN_HEALTH,
    R.INBOUND_ERRORED_STREAMS,
    R.INBOUND_ABANDONED_STREAMS,
    R.INBOUND_CANCELLED_STREAMS,
    R.INBOUND_SUCCESSFUL_STREAMS,
    R.GLOBAL_ERROR,
    R.INBOUND_GLOBAL_ERROR_BY_STREAM
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R ON R.SYNC_ID = S.SYNC_ID
WHERE S.SYNC_DIRECTION = 'inbound'
  AND (
      R.INBOUND_ERRORED_STREAMS    IS NOT NULL
      OR R.INBOUND_ABANDONED_STREAMS IS NOT NULL
      OR R.GLOBAL_ERROR              IS NOT NULL
      OR S.HEALTH_STATE              IN ('FAILED', 'INCOMPLETE')
  )
QUALIFY ROW_NUMBER() OVER (PARTITION BY S.SYNC_ID ORDER BY R.RUN_START_DATETIME DESC) = 1
ORDER BY S.HEALTH_STATE, S.SYNC_NAME
```

For each result present:
- Which streams errored, were abandoned, and which succeeded
- The `GLOBAL_ERROR` if the entire run failed before streams started
- The `INBOUND_GLOBAL_ERROR_BY_STREAM` JSON — this contains the specific error per failed stream

**Key interpretation rules:**
- `INBOUND_ABANDONED_STREAMS` growing when one stream errors is expected — Omnata stops
  downstream streams after an early failure. Fix the errored stream; abandoned streams
  auto-recover on the next run.
- `GLOBAL_ERROR` set with no `INBOUND_GLOBAL_ERROR_BY_STREAM` = catastrophic failure before
  streams started — likely a connection or platform issue rather than a data problem.
- The same stream erroring across 3+ consecutive runs = persistent failure requiring action.

After surfacing error messages, read `references/error-knowledge-base.md` to classify each
distinct error by origin and type, and present the matching remediation actions.

---

#### Step 4: Per-Stream Detail (optional)

**Goal:** For a specific sync, view the stream-level JSON breakdowns from the last run.

```sql
SELECT
    S.SYNC_NAME,
    R.SYNC_RUN_ID,
    R.RUN_START_DATETIME,
    R.INBOUND_STREAM_TOTAL_COUNTS,
    R.INBOUND_STREAM_NEW_COUNTS,
    R.INBOUND_STREAM_CHANGED_COUNTS,
    R.INBOUND_STREAM_DELETED_COUNTS,
    R.INBOUND_ERRORED_STREAMS,
    R.INBOUND_COMPLETED_STREAMS,
    R.INBOUND_SUCCESSFUL_STREAMS,
    R.INBOUND_ABANDONED_STREAMS,
    R.INBOUND_CANCELLED_STREAMS
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON R.SYNC_ID = S.SYNC_ID
WHERE R.SYNC_ID = <sync_id>
QUALIFY ROW_NUMBER() OVER (PARTITION BY R.SYNC_ID ORDER BY R.RUN_START_DATETIME DESC) = 1
```

Present the stream-level JSON objects in a readable format. Highlight any streams in
`INBOUND_ERRORED_STREAMS` or `INBOUND_ABANDONED_STREAMS`.

---

#### Step 5: Stream Cursor State (optional)

**Goal:** Inspect where each stream is currently positioned (its cursor / watermark), to
determine if a stream needs a full refresh or if state may be corrupt.

```sql
SELECT
    SYNC_ID,
    SYNC_NAME,
    INBOUND_LATEST_STREAMS_STATE,
    INBOUND_STREAMS_CONFIGURATION,
    INBOUND_LATEST_STREAMS_SCHEMA
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_ID = <sync_id>
```

The `INBOUND_LATEST_STREAMS_STATE` JSON contains each stream's cursor position — for
example, a timestamp watermark or a page token. Present this in a readable format:
- List each stream and its current state value
- A `null` or empty state means the stream will do a full refresh on its next run
- A stale cursor (very old timestamp) may explain why a stream is pulling large volumes

---

#### Step 6: Stream Audit Trail (optional)

**Goal:** For a specific failing stream, find the last time it successfully synced records.

```sql
SELECT
    H.SYNC_RUN_ID,
    H.EVENT_DATETIME,
    H.INBOUND_STREAM_NAME,
    H.INBOUND_IS_DELETED,
    COUNT(*) AS RECORD_COUNT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RECORD_STATE_HISTORY H
WHERE H.SYNC_ID = <sync_id>
  AND H.INBOUND_STREAM_NAME = '<stream_name>'
GROUP BY 1, 2, 3, 4
ORDER BY H.EVENT_DATETIME DESC
LIMIT 20
```

This shows the most recent runs where this stream processed records — establishing when it
last worked correctly and how much history has been affected by the current failure.

---

### Common Stream Error Patterns

| Error pattern | Likely cause | Suggested action |
|---|---|---|
| Auth / token error | Connection credentials expired or revoked | Re-authenticate the connection in Omnata UI |
| Rate limit error | The source API is throttling requests | Reduce tuning parameters; run less frequently |
| Schema / type error | Source app returned a changed field type or new field added | Trigger a full refresh for that stream; if the normalized view is also stale or missing columns, follow the **Normalized View Troubleshooting** section below |
| Timeout / cancellation | Stream takes too long to complete | Increase `time_limit_mins` or tune batch size |
| One stream errors, others abandoned | Early failure stops downstream streams | Fix the errored stream; abandoned streams auto-recover |
| `GLOBAL_ERROR` set (no stream-level errors) | Catastrophic failure before streams started | Check connection health; may need support investigation |

---

### Stopping Points

- After Step 1 if the user only needed to identify the sync or check overall inbound health
- After Step 2 if the user wanted run history and freshness trends only
- After Step 3 if the user wants to understand which streams are failing and why
- After Step 4 if the user needs per-stream record counts from the last run
- After Step 5 if the user wants to inspect or reset the stream cursor state
- Offer next steps after Step 3: re-authenticate the connection, trigger a full refresh,
  adjust tuning parameters, or escalate via `references/support-handoff.md`

---

### Normalized View Troubleshooting

Omnata lands inbound data in raw tables (`INBOUND_RAW`) and builds normalized views on top
(`INBOUND_NORMALIZED`) that flatten `RECORD_DATA` JSON into typed columns. Problems with
those views are distinct from sync failures — the data may be arriving correctly but the
view definition is wrong, missing, or inaccessible.

**The two-step fix — always in this order:**

1. **Refresh schemas** — re-fetches the JSON schema from the source app's API and updates
   what Omnata knows about the stream's fields. Required when the source schema has changed
   or a plugin upgrade altered field definitions.
2. **Recreate views** — drops and rebuilds the normalized view SQL based on the currently
   stored schema.

If the schema is already correct (e.g. a view was accidentally dropped), only step 2 is needed.
If the schema has drifted, both steps are needed in order.

#### NV Step 1: Diagnose the Symptom

**If the user hasn't specified which sync the view belongs to, ask before running anything.** A stream named 'contact' or 'account' may exist across multiple syncs. The sync slug is required for all subsequent steps. Ask: *"Which sync does this view belong to?"*

| Symptom | Likely cause | Path |
|---|---|---|
| View throws SQL compilation error when queried | View definition stale after plugin update or schema change | Both steps |
| Columns added to source not appearing in view | Schema refresh not triggered | Both steps |
| Deleted source columns still showing with null values | View not rebuilt after schema change | Both steps |
| View doesn't exist in `INBOUND_NORMALIZED` | View creation failed, or view was dropped | Recreate only (unless schema is also missing) |
| Access denied / cannot query the view | Grants lost or permissions misconfigured | Grants check first |

**Identify the configured (active) streams for this sync:**

```sql
SELECT
    SYNC_SLUG,
    OBJECT_KEYS(INBOUND_STREAMS_CONFIGURATION:included_streams) AS CONFIGURED_STREAMS,
    INBOUND_STORAGE_CONFIGURATION
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_SLUG = '<sync_slug>'
```

`CONFIGURED_STREAMS` returns the list of streams actually selected in the sync configuration.
This is the source of truth for which streams are active — use this list when deciding which
streams to refresh or recreate.

> **Important:** `GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS` (below) returns definitions for
> **all streams the plugin exposes**, not just the ones configured in this sync. Do not use
> it to determine which streams are active. Always use `CONFIGURED_STREAMS` above instead.

**Ask the user:** Present the configured stream list and ask whether they want to refresh/recreate
**all** configured streams or only specific ones. Use their answer to build the `ARRAY_CONSTRUCT()`
argument for the procedures in NV Step 3/4.

To preview current view definitions (optional — useful for debugging view SQL):

```sql
CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
    '<sync_slug>',
    'main'
);
```

Returns each stream's `table_name`, `view_body`, `snowflake_columns`, and `joins`. Note: this
returns ALL streams the plugin knows about, not just configured ones.

---

#### NV Step 2: Grants Check (access denied symptom only)

Before investigating the view itself, check whether the view exists and what grants are on it.

**Does the view exist?**

```sql
SHOW VIEWS LIKE '%<stream_name>%' IN SCHEMA <database>.<schema>;
```

If absent, skip to NV Step 4 (view missing). If present, check grants:

```sql
SHOW GRANTS ON VIEW <database>.<schema>."<view_name>";
```

Look for a `SELECT` privilege covering the user's role. Then check schema type:

```sql
SHOW SCHEMAS LIKE '%<schema_name>%' IN DATABASE <database>;
```

Check `IS_MANAGED_ACCESS`. In a managed access schema, only the schema owner can grant
privileges — direct `GRANT SELECT` by other roles silently fails.

| Finding | Action |
|---|---|
| `SELECT` exists for the user's role | Grants are fine — investigate view content instead |
| No `SELECT` for the user's role | `GRANT SELECT ON VIEW <db>.<schema>."<view>" TO ROLE <role>` — or grant the `OMNATA_ADMINISTRATOR` app role |
| Managed access schema, direct grant failed | `GRANT DATABASE ROLE <db>.OMNATA_ROLE TO ROLE <user_role>` — database role grants survive view recreation |
| View doesn't exist | Proceed to NV Step 4 |

---

#### NV Step 3: Fix — Schema Stale (SQL errors, missing or extra columns)

**Option A — Omnata UI:**
1. Navigate to the sync in the Omnata app
2. Go to the **Data** tab
3. Under **Normalized view schemas**, expand **View schema details**
4. Click **Refresh Schemas** — wait for completion
5. Click **Recreate All Views**

**Option B — Stored procedures** (full parameter reference: "Inbound actions" below):

**Step 1 — Refresh schemas from the source app:**

This overwrites the stored stream schemas with the source app's latest. Columns removed in the source drop out of the normalized views at the next recreate. Tell the user before running it.

**Before running:** this overwrites the stored stream schemas with the source app's latest. Tell the user, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.REFRESH_INBOUND_STREAM_SCHEMAS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT()   -- empty = all streams; or ARRAY_CONSTRUCT('issues', 'projects')
);
```

Confirm the returned OBJECT shows `"success": true` before proceeding.

**Step 2 — Recreate normalized views:**

This drops and rebuilds the views. Queries running against them at that moment fail. Grants made on the views are kept, since the app recreates them with `copy grants`. Tell the user before running it.

**Before running:** this drops and rebuilds the normalized views, so queries running against them at that moment fail. Tell the user, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.RECREATE_INBOUND_NORMALIZED_VIEWS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT(),  -- empty = all streams; or specific stream names
    TRUE                -- IGNORE_ERRORS: TRUE = skip failures; FALSE = halt on first error
);
```

The result object:

```json
{
  "data": {
    "streams_recreated": ["issues", "projects"],
    "streams_failed": [],
    "streams_skipped_due_to_missing_schema": []
  },
  "success": true
}
```

| Result field | Meaning |
|---|---|
| `streams_recreated` | Views successfully rebuilt |
| `streams_failed` | View creation failed — check the error |
| `streams_skipped_due_to_missing_schema` | Schema not stored — re-run `REFRESH_INBOUND_STREAM_SCHEMAS` for these streams, then retry |

If `streams_skipped_due_to_missing_schema` is non-empty, re-run the refresh targeting those
stream names explicitly, then call recreate again.

---

#### NV Step 4: Fix — View Missing

Check whether the schema is stored — if yes, only recreate is needed:

```sql
CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
    '<sync_slug>',
    'main'
);
```

If the stream appears with a non-empty `view_body` → schema intact, run recreate only.
If the stream is absent or `view_body` is empty → run refresh first, then recreate.

**Before running:** this drops and rebuilds the normalized views, so queries running against them at that moment fail. Tell the user, and get their confirmation.

```sql
-- Recreate a specific stream only:
CALL OMNATA_SYNC_ENGINE.API.RECREATE_INBOUND_NORMALIZED_VIEWS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT('<stream_name>'),
    TRUE
);
```

---

#### NV Step 5: Verify

**Confirm the view was recreated** by checking its creation timestamp:

```sql
SHOW VIEWS LIKE '%<stream_name>%' IN SCHEMA <database>.<normalized_schema>;
```

Check the `created_on` column — it should reflect the time of the `RECREATE_INBOUND_NORMALIZED_VIEWS`
call. If the timestamp is old, the view was not actually rebuilt (check for errors in the recreate
result above).

**Confirm the view is queryable:**

```sql
SELECT COUNT(*) AS ROW_COUNT FROM <database>.<normalized_schema>.<view_name>;
```

`<view_name>` is the normalized view's name, by default `<sync_slug>_main_<stream_name>` in double quotes, since it's case-sensitive.

**Confirm column count matches expectations:**

```sql
SELECT COUNT(*) AS COLUMN_COUNT
FROM <database>.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '<normalized_schema>'
  AND TABLE_NAME = '<sync_slug>_main_<stream_name>';
```

Grants made on the view survive recreation, because the app recreates views with `copy grants`. If the user lost access anyway, check the grants with NV Step 2.

Escalate to `references/support-handoff.md` if `streams_failed` is non-empty after retry
and the error is not self-explanatory.

### Inbound actions

#### Refresh Inbound Stream Schemas

Polls the source application to discover new or changed object schemas for the specified inbound
sync. Run this when new fields or objects have been added in the source app and are not yet
visible in Snowflake.

**Minimum version: v3.60**

**Before running:** this overwrites the stored stream schemas with the source app's latest. Tell the user, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.REFRESH_INBOUND_STREAM_SCHEMAS(
    '<sync_slug>',            -- SYNC_SLUG (VARCHAR)
    'main',                   -- BRANCH_NAME (VARCHAR)
    ARRAY_CONSTRUCT()         -- STREAM_NAMES (ARRAY) — empty array = all streams
);
```

To refresh specific streams only:

**Before running:** this overwrites the stored stream schemas with the source app's latest. Tell the user, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.REFRESH_INBOUND_STREAM_SCHEMAS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT('Account', 'Contact')
);
```

> **Note:** This procedure updates the schema metadata stored in Omnata. It does not
> recreate the normalized views. To rebuild the views after refreshing schemas, call
> `RECREATE_INBOUND_NORMALIZED_VIEWS` next.

---

#### Recreate Inbound Normalized Views

Rebuilds the normalized views in `INBOUND_NORMALIZED` that flatten the `RECORD_DATA` JSON
column from raw inbound tables. Run this after schema refresh, when views are missing, or when
column definitions are stale.

**Minimum version: v3.17. `IGNORE_ERRORS` parameter added: v3.126**

**Before running:** this drops and rebuilds the normalized views, so queries running against them at that moment fail. Tell the user, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.RECREATE_INBOUND_NORMALIZED_VIEWS(
    '<sync_slug>',            -- SYNC_SLUG (VARCHAR)
    'main',                   -- BRANCH_NAME (VARCHAR)
    ARRAY_CONSTRUCT(),        -- STREAM_NAMES (ARRAY) — empty array = all streams
    TRUE                      -- IGNORE_ERRORS (BOOLEAN) — skip individual view failures
);
```

> **Order of operations:** Always run `REFRESH_INBOUND_STREAM_SCHEMAS` before
> `RECREATE_INBOUND_NORMALIZED_VIEWS` when fixing stale schema or missing columns.
> Refreshing schemas without recreating views leaves the views with old column definitions.

> **Warning:** Recreating views drops and rebuilds them, so queries running against them
> at that moment fail. Grants made on the views are kept, because the app recreates them with `copy grants`.

---

#### Get Inbound View Definitions

Returns the `CREATE VIEW` definitions for all normalized views in an inbound sync, as an OBJECT. Use it to inspect the columns each view exposes, or to create the views yourself (e.g. in dbt).

```sql
CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
    '<sync_slug>',
    'main'
);
```

For one stream: `CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_STREAM_VIEW_DEFINITION('<sync_slug>', 'main', '<stream_name>', false)`.

---

#### Full Refresh of Inbound Streams

Marks streams so the **next run** re-reads them in full. `TRUNCATE = true` empties the raw tables first; `false` keeps existing rows and merges over them.

**Before running:** the next run re-reads these streams in full, which uses warehouse credits and API rate limits; with `TRUNCATE` true, the tables are emptied first. Get the user's confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_STREAMS_FOR_FULL_REFRESH(
    <sync_id>,                              -- SYNC_ID (FLOAT)
    'main',                                 -- BRANCH_NAME (VARCHAR)
    ARRAY_CONSTRUCT('Account', 'Contact'),  -- STREAMS (ARRAY)
    false                                   -- TRUNCATE (BOOLEAN)
);
```

- Undo before the next run with `UNMARK_STREAMS_FOR_FULL_REFRESH(SYNC_ID, BRANCH_NAME, STREAMS)`.
- `MARK_PLUGIN_FOR_FULL_REFRESH(PLUGIN_FQN, TRUNCATE)` marks **every stream of every sync and branch** for a plugin. The next runs re-read everything, which uses warehouse credits and the source app's API rate limits, and with `truncate = true` empties the tables first. List the affected syncs and branches for the user and confirm before using it.

**Recurring full refresh.** Set a schedule. It's checked at each run and doesn't add extra runs:

```sql
CALL OMNATA_SYNC_ENGINE.API.SET_FULL_REFRESH_SCHEDULE(
    '<sync_slug>', 'main',
    OBJECT_CONSTRUCT('frequency', '<cron_expression>', 'frequency_name', 'Weekly', 'truncate_inbound', false)
);
```

`<cron_expression>` is a five-field cron schedule followed by a timezone, for example midnight UTC every Sunday. `frequency_name` is one of `Always`, `Daily`, `Weekly`, `Monthly nth day`, `Monthly last day`, `Monthly nth weekday`, `Monthly last weekday`, `Custom`.

---

#### Move an Inbound Sync's Tables

Changes where an existing inbound sync's raw tables and normalized views live, **and moves the existing tables and views** to the new location. Changing the default storage location doesn't do this.

**Before running:** the next run moves the sync's tables and views and deletes the old ones. Show the user the old and new locations, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.SET_INBOUND_SYNC_LOCATION(
    NULL,               -- SYNC_ID (FLOAT) — or NULL if using slug
    '<sync_slug>',      -- SYNC_SLUG (VARCHAR)
    <storage_location>, -- INBOUND_STORAGE_LOCATION (OBJECT), same keys as INBOUND_STORAGE_LOCATION
    NULL                -- MULTI_ACCOUNT_KEY (VARCHAR) — only for multi-account syncs
);
```

Design and preview the location first with `references/data-management.md`.

The move happens at the **next run**, not when you call this. That run moves the tables and views (it doesn't copy them), deletes the old ones, and moves open branches too. Suggest one run straight away to confirm it. Tables from streams the sync no longer uses stay behind; offer to drop them.

---

#### Clean Up Orphaned Inbound Objects

Lists or drops inbound tables or views in the Sync Engine's database that no longer belong to any sync. Always run with `LIST_ONLY = true` first and check the list with the user.

**Before running:** with `LIST_ONLY` false this drops the listed objects. Run it with `true` first, show the user the list, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.CLEANUP_INBOUND_OBJECTS('table', true);  -- OBJECT_TYPE 'table' or 'view'; LIST_ONLY
```

---

#### Override Inbound Stream State

`SET_INBOUND_SYNC_STATE(SYNC_SLUG, STREAM_NAME, STREAM_STATE)`, or `SET_INBOUND_SYNC_STATE(SYNC_SLUG, STREAMS_STATE)` keyed by stream name, overwrites the stored cursor state. **Only under the direction of Omnata support**: plugins maintain their own state, and a wrong state can skip or duplicate data.

---

## Part 3: Outbound syncs

Investigate outbound syncs — those that push records from a Snowflake source table to an
external application. Covers run history, failed records, error patterns, and stuck records.

### Background

Outbound syncs read from a Snowflake source table and apply records to the destination app.
Each record has an `APPLY_STATE` that reflects whether it synced successfully:

| APPLY_STATE | Meaning |
|---|---|
| `SUCCESS` | Record applied in the destination app |
| `DESTINATION_FAILURE` | Destination app rejected the record — error in `LAST_RESULT` |
| `SOURCE_FAILURE` | Record failed pre-flight checks before reaching the destination |
| `DELAYED` | Not processed this run due to rate limiting or cancellation — will retry |
| `RESYNC_REQUESTED` | Manually flagged for resync |
| `SKIPPED_ONCE` | Most recent change was manually skipped; future changes will sync normally |
| `SKIPPED_ALWAYS` | Permanently excluded from the sync |

`SOURCE_FAILURE` means the problem is on the Snowflake side (transform error, field mapping
issue). `DESTINATION_FAILURE` means the destination app rejected the record — look at
`LAST_RESULT` for the error from the API.

### Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

---

### Workflow

#### Step 1: Identify the Sync

If the user named a specific sync, find its `SYNC_ID`:

```sql
SELECT
    SYNC_ID,
    SYNC_NAME,
    SYNC_SLUG,
    HEALTH_STATE,
    RUN_STATE,
    OUTBOUND_SOURCE_DATABASE,
    OUTBOUND_SOURCE_SCHEMA,
    OUTBOUND_SOURCE_TABLE,
    SPLIT_PART(PLUGIN_FQN, '__', 2) AS APP
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_DIRECTION = 'outbound'
  AND (SYNC_NAME ILIKE '%<user_provided_name>%'
       OR SYNC_SLUG ILIKE '%<user_provided_name>%')
ORDER BY SYNC_NAME
```

If the user didn't name a sync, show all outbound syncs that currently have failures:

```sql
SELECT
    S.SYNC_NAME,
    S.SYNC_ID,
    S.HEALTH_STATE,
    SPLIT_PART(S.PLUGIN_FQN, '__', 2) AS APP,
    COUNT(*) AS FAILED_RECORD_COUNT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON R.SYNC_ID = S.SYNC_ID
WHERE R.APPLY_STATE IN ('DESTINATION_FAILURE', 'SOURCE_FAILURE')
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC
```

Ask the user to confirm which sync to investigate if multiple are returned.

---

#### Step 2: Run History

**Goal:** Show recent runs with durations, record counts, and failure breakdown.

```sql
SELECT
    R.SYNC_RUN_ID,
    R.RUN_START_DATETIME,
    R.RUN_END_DATETIME,
    DATEDIFF('second', R.RUN_START_DATETIME, R.RUN_END_DATETIME) AS DURATION_SECS,
    R.HEALTH_STATE,
    R.CANCELLED_DATETIME IS NOT NULL                                  AS WAS_CANCELLED,
    R.OUTBOUND_TOTAL_COUNT                                            AS TOTAL,
    R.OUTBOUND_APPLY_STATE_COUNTS:SUCCESS::INTEGER                    AS SUCCESS,
    R.OUTBOUND_APPLY_STATE_COUNTS:DESTINATION_FAILURE::INTEGER        AS DEST_FAIL,
    R.OUTBOUND_APPLY_STATE_COUNTS:SOURCE_FAILURE::INTEGER             AS SRC_FAIL,
    R.OUTBOUND_APPLY_STATE_COUNTS:DELAYED::INTEGER                    AS DELAYED,
    R.OUTBOUND_APPLY_REASON_COUNTS:CHANGE_CRITERIA_MET::INTEGER       AS CHANGED,
    R.OUTBOUND_APPLY_REASON_COUNTS:RESYNC_REQUESTED::INTEGER          AS RESYNC,
    R.OUTBOUND_APPLY_REASON_COUNTS:PREVIOUSLY_FAILED::INTEGER         AS RETRY,
    R.GLOBAL_ERROR
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R
WHERE R.SYNC_ID = <sync_id>
ORDER BY R.RUN_START_DATETIME DESC
LIMIT 20
```

Present as a table, most-recent first. Format `DURATION_SECS` as `Xm Ys`. Flag:
- Runs where `HEALTH_STATE != 'HEALTHY'`
- Cancelled runs (`WAS_CANCELLED = TRUE`)
- Runs with zero records processed (empty runs — normal but worth noting if unexpected)
- Consecutive failures

After the table, summarise the trend:
- Success rate across shown runs
- Average duration (exclude cancelled)
- Whether `DEST_FAIL` or `SRC_FAIL` counts are growing, stable, or shrinking
- Surface any `GLOBAL_ERROR` values and offer to investigate further

---

#### Step 3: Failed Records

**Goal:** List all records currently in a failed state with their error details.

```sql
SELECT
    R.IDENTIFIER,
    R.APP_IDENTIFIER,
    R.APPLY_STATE,
    R.SYNC_ACTION,
    R.FAILURE_COUNT,
    R.LAST_RESULT,
    R.LAST_RUN_APPLY_REASON,
    R.APPLY_STATE_DATETIME,
    R.RECORD_STATE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
WHERE R.SYNC_ID = <sync_id>
  AND R.APPLY_STATE IN ('DESTINATION_FAILURE', 'SOURCE_FAILURE')
ORDER BY R.FAILURE_COUNT DESC, R.APPLY_STATE_DATETIME DESC
LIMIT 100
```

Present showing:
- `IDENTIFIER` — the source record's key (e.g. email, ID)
- `APP_IDENTIFIER` — the record's ID in the destination app, if previously synced
- `APPLY_STATE` — `DESTINATION_FAILURE` (app rejected) vs `SOURCE_FAILURE` (Snowflake-side failure)
- `FAILURE_COUNT` — how many times this record has failed
- `LAST_RESULT` — the raw error from the destination API (most important for diagnosis)
- `SYNC_ACTION` — what was being attempted (Create, Update, Delete)

`SOURCE_FAILURE` with `LAST_RUN_APPLY_REASON = 'TRANSFORM_ERROR'` means the Jinja
template or field mapping failed in Snowflake before the record was sent anywhere.

---

#### Step 4: Error Pattern Analysis

**Goal:** Group failures by error message to identify systemic vs one-off issues.

```sql
SELECT
    R.APPLY_STATE,
    R.LAST_RESULT::VARCHAR      AS ERROR_MESSAGE,
    R.SYNC_ACTION,
    COUNT(*)                    AS RECORD_COUNT,
    MIN(R.FAILURE_COUNT)        AS MIN_FAILURES,
    MAX(R.FAILURE_COUNT)        AS MAX_FAILURES
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
WHERE R.SYNC_ID = <sync_id>
  AND R.APPLY_STATE IN ('DESTINATION_FAILURE', 'SOURCE_FAILURE')
GROUP BY 1, 2, 3
ORDER BY 4 DESC
```

Interpret the patterns:
- Same `LAST_RESULT` across many records → systemic issue (auth, rate limit, missing field)
- Varied errors → individual data-quality problems
- High `MAX_FAILURES` → persistently stuck, won't self-resolve
- All `SOURCE_FAILURE` → problem is in the field mapping or source data, not the destination

After surfacing error patterns, read `references/error-knowledge-base.md` to classify each
distinct error by origin and type, and present the matching remediation actions.

---

#### Step 5: Single Record Lookup (optional)

If the user asks about a specific record by its identifier:

```sql
SELECT
    R.IDENTIFIER,
    R.APP_IDENTIFIER,
    R.RECORD_STATE,
    R.APPLY_STATE,
    R.SYNC_ACTION,
    R.FAILURE_COUNT,
    R.LAST_RESULT,
    R.TRANSFORMED_RECORD,
    R.LAST_RUN_APPLY_REASON,
    R.APPLY_STATE_DATETIME,
    R.RECORD_STATE_DATETIME
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
WHERE R.SYNC_ID = <sync_id>
  AND R.IDENTIFIER = '<identifier_value>'
```

Show `TRANSFORMED_RECORD` (the post-transformation payload Omnata actually attempted to
send) alongside `LAST_RESULT` — this reveals whether the data issue is in the source
values or the mapping logic.

---

#### Step 6: Stuck & Delayed Records

**Goal:** Find records that are not making progress across runs.

A record is stuck when it has been in a non-progressing state for multiple runs:
- `DELAYED` — rate-limited or run cancelled before processing; will retry next run
- `RESYNC_REQUESTED` — flagged for resync but the sync may not be running
- `ACTIVE` — marked in-progress from a run that may have died
- High `FAILURE_COUNT` in `DESTINATION_FAILURE` / `SOURCE_FAILURE` — repeatedly failing

**Cross-sync overview:**

```sql
SELECT
    S.SYNC_NAME,
    S.HEALTH_STATE                          AS SYNC_HEALTH,
    R.APPLY_STATE,
    COUNT(*)                                AS RECORD_COUNT,
    MAX(R.FAILURE_COUNT)                    AS MAX_FAILURE_COUNT,
    ROUND(AVG(R.FAILURE_COUNT), 1)          AS AVG_FAILURE_COUNT,
    MIN(R.APPLY_STATE_DATETIME)             AS OLDEST_STUCK_SINCE,
    MAX(R.APPLY_STATE_DATETIME)             AS MOST_RECENT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON R.SYNC_ID = S.SYNC_ID
WHERE R.APPLY_STATE IN ('DELAYED', 'RESYNC_REQUESTED', 'ACTIVE')
   OR (R.APPLY_STATE IN ('DESTINATION_FAILURE', 'SOURCE_FAILURE') AND R.FAILURE_COUNT >= 3)
GROUP BY 1, 2, 3
ORDER BY 4 DESC
```

**Drill into a specific sync:**

```sql
SELECT
    R.IDENTIFIER,
    R.APP_IDENTIFIER,
    R.APPLY_STATE,
    R.SYNC_ACTION,
    R.FAILURE_COUNT,
    R.LAST_RESULT,
    R.LAST_RUN_APPLY_REASON,
    R.APPLY_STATE_DATETIME,
    DATEDIFF('day', R.APPLY_STATE_DATETIME, CURRENT_TIMESTAMP()) AS DAYS_STUCK
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE R
WHERE R.SYNC_ID = <sync_id>
  AND (
      R.APPLY_STATE IN ('DELAYED', 'RESYNC_REQUESTED', 'ACTIVE')
      OR (R.APPLY_STATE IN ('DESTINATION_FAILURE', 'SOURCE_FAILURE') AND R.FAILURE_COUNT >= 3)
  )
ORDER BY R.FAILURE_COUNT DESC, R.APPLY_STATE_DATETIME ASC
LIMIT 100
```

**Remediation by state:**

| State | Recommended action |
|---|---|
| Many `DELAYED` records | Sync is likely rate-limited — reduce `max_concurrent_uploads` in tuning parameters |
| `RESYNC_REQUESTED` not moving | Check if the sync is paused or not scheduled to run |
| High `FAILURE_COUNT` with consistent error | Fix the underlying issue — records retry automatically on next run |
| `ACTIVE` records, no recent run | Stale state from a cancelled run — clears on next successful run |
| `SOURCE_FAILURE` | Problem is in field mapping or source data, not the destination |

---

### Stopping Points

- After Step 1 if the user only needed to identify the sync
- After Step 2 if the user wanted run history and trends only
- After Step 4 if the user wants to understand error patterns before deciding on action
- After Step 5 if the user asked about a specific record
- Offer next steps after Step 4 or Step 6: skip failing records, request resync, fix source data, re-authenticate connection, or escalate via `references/support-handoff.md`

### Outbound record actions

These apply to **outbound** syncs. Each record's state is held by Omnata (`DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE`), not in your source table, so change it with these procedures, not by editing source data.

| APPLY_STATE | Meaning |
|---|---|
| `SUCCESS` | Last attempt succeeded |
| `DESTINATION_FAILURE` | Failed to write to destination (endpoint error) |
| `SOURCE_FAILURE` | Failed due to source data or mapping error |
| `RESYNC_REQUESTED` | Queued for re-send on next run |
| `SKIPPED_ONCE` | Most recent change was manually skipped; future changes will sync normally |
| `SKIPPED_ALWAYS` | Permanently excluded from syncing |
| `DELAYED` | Waiting due to rate limiting |
| `ACTIVE` | Currently being processed |
| `NOT_REQUIRED` | No action needed (record already in sync with destination) |

#### Resync Records

Queues records to be sent again on the next run, whether or not they previously succeeded.

**Before running:** this changes which records are sent on the next run. Show the user the record IDs, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_RECORDS_FOR_RESYNC(
    '<sync_slug>',                                 -- SYNC_SLUG
    'main',                                        -- BRANCH_NAME
    NULL,                                          -- SYNC_ACTION — optional, e.g. 'Create'; must be valid for the sync's strategy
    ARRAY_CONSTRUCT('<record_id>', '<record_id>')  -- RECORD_IDS — values of the source table's ID column
);
```

#### Skip Records

**Before running:** skipped records aren't sent to the destination. Show the user the record IDs, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_RECORDS_FOR_SKIP(
    '<sync_slug>', 'main',
    'SKIPPED_ONCE',                    -- or 'SKIPPED_ALWAYS'
    ARRAY_CONSTRUCT('<record_id>')
);
```

#### Bulk: by criteria

`MARK_MATCHING_RECORDS_FOR_RESYNC(sync_slug, branch_name, sync_action, criteria)`, `MARK_MATCHING_RECORDS_FOR_SKIP(sync_slug, branch_name, apply_state, criteria)` and `MARK_MATCHING_RECORDS_AS_SUCCESSFUL(sync_slug, branch_name, criteria)` act on every record that matches `criteria`, an OBJECT with any of:
- `apply_statuses`: array of `APPLY_STATE` values, e.g. `['DESTINATION_FAILURE']`
- `record_states`: array of record states
- `sync_actions`: array of sync actions
- `search_terms`: array of strings matched against the transformed record

**Before running:** this acts on every matching record. Show the user the count from `OUTBOUND_SYNC_RECORD_STATE`, and get their confirmation.

```sql
-- Example: resync every record that failed at the destination
CALL OMNATA_SYNC_ENGINE.API.MARK_MATCHING_RECORDS_FOR_RESYNC(
    '<sync_slug>', 'main', NULL,
    OBJECT_CONSTRUCT('apply_statuses', ARRAY_CONSTRUCT('DESTINATION_FAILURE'))
);
```

Before a bulk call, count the matching records in `DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE` and confirm with the user. `MARK_MATCHING_RECORDS_AS_SUCCESSFUL` stops Omnata retrying those records; use it only when the user is sure they're already correct in the destination.

---

## Part 4: Sync lifecycle

### Run a Sync

Triggers a sync run for main or a branch.

**Before running:** a run uses warehouse credits and the source app's API rate limits, and outbound runs write to the destination app. Get the user's confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(
    NULL,                              -- SYNC_ID (FLOAT)     — set to NULL when using slug
    '<sync_slug>',                     -- SYNC_SLUG (VARCHAR) — from DATA_VIEWS.SYNC
    'main',                            -- BRANCH_NAME (VARCHAR) — 'main', or a branch name
    'external',                        -- RUN_SOURCE_NAME (VARCHAR)
    {'triggered_by': 'cortex_code'},   -- RUN_SOURCE_METADATA (OBJECT)
    true,                              -- WAIT_FOR_COMPLETION (BOOLEAN)
    true,                              -- RAISE_ERRORS (BOOLEAN)
    CURRENT_USER()                     -- CURRENT_USER (VARCHAR)
);
```

| Parameter | Type | Notes |
|---|---|---|
| `SYNC_ID` | FLOAT | Use this **or** `SYNC_SLUG`, not both. Set the unused one to `NULL`. |
| `SYNC_SLUG` | VARCHAR | Preferred — human-readable and unambiguous. From `DATA_VIEWS.SYNC.SYNC_SLUG`. |
| `BRANCH_NAME` | VARCHAR | `'main'` for the main sync (also the default when `NULL`), or a branch name. See `references/branching.md`. |
| `RUN_SOURCE_NAME` | VARCHAR | Label for the trigger origin — use `'external'` for Cortex Code-initiated runs. |
| `RUN_SOURCE_METADATA` | OBJECT | Optional metadata attached to the run — useful for audit trail. |
| `WAIT_FOR_COMPLETION` | BOOLEAN | Default `true`: blocks until the run finishes. `false`: returns once the run is enqueued. |
| `RAISE_ERRORS` | BOOLEAN | `true` raises a SQL error if the run fails. Use with `WAIT_FOR_COMPLETION = true`. |
| `CURRENT_USER` | VARCHAR | Needed when the sync or branch has a designated owner (`SET_SYNC_OWNER`): only the owner can run it. |

**Behaviour:**
- If the sync is already running, the call succeeds without starting another run and returns `wasAlreadyRunning: true`, unless the current run has passed its time limit.
- A paused sync or branch raises an error. Resume it first.
- Main must have a connection.

The result includes `syncRunId`, and `syncRunHealth` when waiting. If it shows `[object Object]`, read it with `SELECT TO_JSON($1) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))`. To check a run:

```sql
SELECT SYNC_RUN_ID, HEALTH_STATE, RUN_START_DATETIME, RUN_END_DATETIME, INBOUND_TOTAL_COUNT, GLOBAL_ERROR
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN
WHERE SYNC_ID = (SELECT SYNC_ID FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_SLUG = '<sync_slug>')
ORDER BY RUN_START_DATETIME DESC
LIMIT 1;
```

### Cancel a Sync Run

There is no cancel procedure available to customer roles: `CANCEL_SYNC_RUN` exists but isn't granted to the app roles. To stop a running sync, use the Omnata UI. To stop future runs, pause the sync.

---

### Pause a Sync

Pauses a sync or branch, and suspends its Snowflake scheduler task if Omnata manages the schedule. It fails if the sync is currently running; wait for the run to finish first. If it's already paused, it returns `wasAlreadyPaused: true`.

**Before running:** a paused sync stops running on its schedule until it's resumed. Get the user's confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.PAUSE_SYNC(
    '<sync_slug>',  -- SYNC_SLUG (VARCHAR)
    'main'          -- BRANCH_NAME (VARCHAR) — 'main' (or NULL), or a branch name
);
```

---

### Resume a Sync

Re-enables a paused sync or branch and resumes its scheduler task. It doesn't trigger a run; the sync runs at its next scheduled time. If it isn't paused, it returns `wasAlreadyResumed: true`.

**Before running:** ask why the sync was paused, since it may have been paused on purpose. Resuming restarts its scheduled runs. Get the user's confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.RESUME_SYNC(
    '<sync_slug>',  -- SYNC_SLUG (VARCHAR)
    'main'          -- BRANCH_NAME (VARCHAR) — 'main' (or NULL), or a branch name
);
```

> **If resuming and also triggering immediately:** Call `RESUME_SYNC` first, then `RUN_SYNC`.

---

### Rename, Reschedule or Assign an Owner

```sql
-- Rename (display name only)
CALL OMNATA_SYNC_ENGINE.API.SET_SYNC_NAME('<sync_slug>', '<new name>');

-- Change the schedule. MULTI_ACCOUNT is false unless the sync is multi-account.
-- BRANCH_NAME NULL means main. The schedule object has the same shape as SYNC_SCHEDULE in configure-syncs.md.
CALL OMNATA_SYNC_ENGINE.API.SET_SYNC_SCHEDULE(
    '<sync_slug>', false,
    OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    NULL
);

-- Set an owner on a sync or branch: only that user can then configure or run it.
-- Pass NULL as the owner to clear it.
CALL OMNATA_SYNC_ENGINE.API.SET_SYNC_OWNER('<sync_slug>', '<branch_name or NULL>', '<snowflake_user>');
```

**Change a sync's slug** with `SET_SYNC_SLUG(SYNC_ID, NEW_SLUG)`. Use with caution: external tools such as dbt, and `RUN_SYNC` calls in scheduled jobs, may still use the old slug.

---

### Delete a Sync

Permanently deletes a sync. Irreversible. **For inbound syncs, its raw tables and normalized views are deleted with it**, so the synced data is gone. Before calling, show the user the sync's name and slug, and for inbound syncs the tables and views that will go, and confirm the data isn't needed. Offer to copy it out first (below).

**Before running:** this permanently deletes the sync and, for inbound syncs, its raw tables and normalized views. Show the user the sync and what will be deleted, and get their confirmation.

```sql
CALL OMNATA_SYNC_ENGINE.API.DELETE_SYNC(
    '<sync_slug>',  -- SYNC_SLUG (VARCHAR)
    NULL            -- SYNC_ID (NUMBER) — or NULL if using slug
);
```

Returns an OBJECT with `success` = `true` and `data.deleted` = `true`. One call removes:
- the sync record and its configuration
- its raw tables in `OMNATA_SYNC_ENGINE.INBOUND_RAW` (inbound)
- its normalized views in `OMNATA_SYNC_ENGINE.INBOUND_NORMALIZED` (inbound)

The connection and any other syncs on it are untouched. Synced data goes with the raw tables, so if the user wants to keep it, copy it out first (e.g. `CREATE TABLE ... AS SELECT * FROM <normalized view>`).

To delete a connection together with its syncs, see "Clean Up Syncs and Connections" in `references/connection-management.md`.

## Part 5: Pre/post run hooks

Hooks run your own stored procedure at the start or end of every sync run. They aren't configured in the Omnata UI: you create a procedure with a reserved name, and the Sync Engine finds and calls it.

### How they work

| Hook | Procedure name | When it runs |
|---|---|---|
| Pre-run | `SYNC_RUN_PRE_HOOK` | At the start of each sync run |
| Post-run | `SYNC_RUN_POST_HOOK` | At the end of each sync run, whatever its outcome |

- **Discovery:** the engine looks for procedures with these names **anywhere in the account** that take a single `OBJECT` argument. Every one it can see is called.
- **They run for every sync and branch.** To act on particular syncs only, check `sync_slug` (or `branch_id`) in the payload and return early otherwise.
- **Requirements:** the procedure must be `EXECUTE AS OWNER`, and the app needs `USAGE` on the procedure, its database and its schema.
- **Failures don't affect the sync.** If a hook errors, the engine logs it and carries on; the run's health and `GLOBAL_ERROR` aren't changed. To find hook errors, check the event table (`references/event-table-diagnostics.md`), or log inside the hook.

### Payload

Both hooks receive `sync_run_id`, `sync_id`, `sync_slug` and `branch_id` (null for main), plus `sync`, `connection` and `branch` objects with the columns of the matching `DATA_VIEWS` views.
- **Pre-run** also gets `previous_sync_run_id` and `previous_health_state` (null on the first run).
- **Post-run** also gets `new_health_state` and, for inbound syncs, `streams_with_refreshed_schemas`.

### Example

```sql
CREATE TABLE MY_DB.OPS.SYNC_HOOK_LOG (PAYLOAD OBJECT, LOGGED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());

CREATE OR REPLACE PROCEDURE MY_DB.OPS.SYNC_RUN_POST_HOOK(RESULT OBJECT)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
BEGIN
  IF (:RESULT:sync_slug::VARCHAR != '<sync_slug>') THEN
    RETURN 'skipped';
  END IF;
  INSERT INTO MY_DB.OPS.SYNC_HOOK_LOG (PAYLOAD) SELECT :RESULT;
  -- e.g. CALL MY_DB.TRANSFORMS.REFRESH_CONTACT_DIM();
  RETURN 'logged';
END;

GRANT USAGE ON DATABASE MY_DB TO APPLICATION OMNATA_SYNC_ENGINE;
GRANT USAGE ON SCHEMA MY_DB.OPS TO APPLICATION OMNATA_SYNC_ENGINE;
GRANT USAGE ON PROCEDURE MY_DB.OPS.SYNC_RUN_POST_HOOK(OBJECT) TO APPLICATION OMNATA_SYNC_ENGINE;
```

The procedure runs as its owner, so that role needs the privileges for whatever the hook does (e.g. `INSERT` on the log table).

To see which hooks exist: `SHOW USER PROCEDURES LIKE 'SYNC_RUN_%_HOOK' IN ACCOUNT;`

---

## Part 6: Application settings (support only)

The default inbound storage location (`SET_DEFAULT_INBOUND_STORAGE_LOCATION`) is covered in `references/data-management.md`.

### Set an application setting

Sets an application-level configuration value. Available setting names are not publicly
documented — use only when Omnata support has provided a specific setting name and value.

The procedure is `SET_APP_SETTING(SETTING_NAME, SETTING_VALUE)`. Don't build this call yourself. Run it only with the exact setting name and value Omnata support gave the user, after showing the user the call and getting their yes.

---

## Quick reference

| Procedure | Parameters | Notes |
|---|---|---|
| `RUN_SYNC` | `(SYNC_ID, SYNC_SLUG, BRANCH_NAME, RUN_SOURCE_NAME, RUN_SOURCE_METADATA, WAIT_FOR_COMPLETION, RAISE_ERRORS, CURRENT_USER)` | Trigger a run |
| `PAUSE_SYNC` | `(SYNC_SLUG, BRANCH_NAME)` | Pause a sync or branch |
| `RESUME_SYNC` | `(SYNC_SLUG, BRANCH_NAME)` | Resume a sync or branch |
| `SET_SYNC_NAME` | `(SYNC_SLUG, SYNC_NAME)` | Rename |
| `SET_SYNC_SCHEDULE` | `(SYNC_SLUG, MULTI_ACCOUNT, SYNC_SCHEDULE, BRANCH_NAME)` | Change schedule |
| `SET_SYNC_OWNER` | `(SYNC_SLUG, BRANCH_NAME, OWNER)` | Restrict configure/run to one user |
| `SET_SYNC_SLUG` | `(SYNC_ID, SYNC_SLUG)` | Change slug. Caution: external references |
| `DELETE_SYNC` | `(SYNC_SLUG, SYNC_ID)` | Delete a sync, its raw tables and normalized views. Irreversible. |
| `DELETE_SYNC_BRANCH`, `SYNC_CONFIGURATION_ROLLBACK` | see `references/branching.md` | Delete a branch; copy or roll back configuration |
| `CONFIGURE_OMNATA_OUTBOUND_SYNC` | 21 params — see `references/configure-syncs.md` | Create or update an outbound sync. Idempotent. |
| `CONFIGURE_OMNATA_INBOUND_SYNC` | 28 params (8 required) — see `references/configure-syncs.md` | Create or update an inbound sync. Idempotent. |
| `REFRESH_INBOUND_STREAM_SCHEMAS` | `(SYNC_SLUG, BRANCH_NAME, STREAM_NAMES)` | Pull latest schemas from source app. Min v3.60. |
| `RECREATE_INBOUND_NORMALIZED_VIEWS` | `(SYNC_SLUG, BRANCH_NAME, STREAM_NAMES, IGNORE_ERRORS)` | Rebuild normalized views. Min v3.17. |
| `GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS` | `(SYNC_SLUG, BRANCH_NAME)` | Returns an OBJECT of CREATE VIEW SQL. Use `CALL` |
| `MARK_STREAMS_FOR_FULL_REFRESH` / `UNMARK_STREAMS_FOR_FULL_REFRESH` | `(SYNC_ID, BRANCH_NAME, STREAMS, TRUNCATE)` / `(SYNC_ID, BRANCH_NAME, STREAMS)` | Full refresh on the next run |
| `SET_FULL_REFRESH_SCHEDULE` | `(SYNC_SLUG, BRANCH_NAME, FULL_REFRESH_SCHEDULE)` | Recurring full refresh |
| `SET_INBOUND_SYNC_LOCATION` | `(SYNC_ID, SYNC_SLUG, INBOUND_STORAGE_LOCATION, MULTI_ACCOUNT_KEY)` | Move an existing sync's tables and views |
| `CLEANUP_INBOUND_OBJECTS` | `(OBJECT_TYPE, LIST_ONLY)` | List or drop orphaned inbound objects |
| `CANCEL_SYNC_RUN` | none for customers | Not granted to customer roles. Wait for the run to finish or contact Omnata support |
| `SET_INBOUND_SYNC_STATE` | `(SYNC_SLUG, STREAM_NAME, STREAM_STATE)` or `(SYNC_SLUG, STREAMS_STATE)` | Only on Omnata support instruction. Overwrites cursor state |
| `MARK_RECORDS_FOR_RESYNC` | `(SYNC_SLUG, BRANCH_NAME, SYNC_ACTION, RECORD_IDS)` | Outbound only |
| `MARK_RECORDS_FOR_SKIP` | `(SYNC_SLUG, BRANCH_NAME, APPLY_STATE, RECORD_IDS)` | `SKIPPED_ONCE` or `SKIPPED_ALWAYS` |
| `MARK_MATCHING_RECORDS_FOR_RESYNC` / `_FOR_SKIP` / `_AS_SUCCESSFUL` | `(SYNC_SLUG, BRANCH_NAME, [SYNC_ACTION or APPLY_STATE,] CRITERIA)` | Bulk, by criteria |
| `SET_DEFAULT_INBOUND_STORAGE_LOCATION` | `(OBJECT)` | Default for new syncs. See `references/data-management.md` |
| `SET_APP_SETTING` | `(SETTING_NAME, SETTING_VALUE)` | ⚠️ Undocumented. Use only on Omnata support instruction. |

Connection procedures are listed in `references/connection-management.md`.
