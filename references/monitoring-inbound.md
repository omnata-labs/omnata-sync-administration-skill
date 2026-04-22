<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-monitoring-inbound
description: "Monitor and investigate inbound Omnata syncs — syncs that pull data from an external app into Snowflake. Use when: user asks about inbound sync health, data freshness, when data was last synced, which streams failed, stream error messages, stream cursor state, or why inbound data is stale or missing. Triggers: inbound sync, data freshness, last sync time, when was data synced, stream failed, stream error, inbound stream failure, new records, changed records, stream abandoned, stream cancelled, inbound sync error, stream not syncing."
---

# Omnata Inbound Sync Monitoring

Investigate inbound syncs — those that pull data from an external application into Snowflake.
Covers data freshness, run history, stream-level failures, cursor state, and error diagnosis.

## Background

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

## Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

---

## Workflow

### Step 1: Inbound Sync Overview

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
- Syncs with `RUN_STATE = 'PAUSED'` that should be running

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

### Step 2: Run History

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

### Step 3: Stream Failure Detail

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

### Step 4: Per-Stream Detail (optional)

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

### Step 5: Stream Cursor State (optional)

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

### Step 6: Stream Audit Trail (optional)

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

## Common Stream Error Patterns

| Error pattern | Likely cause | Suggested action |
|---|---|---|
| Auth / token error | Connection credentials expired or revoked | Re-authenticate the connection in Omnata UI |
| Rate limit error | The source API is throttling requests | Reduce tuning parameters; run less frequently |
| Schema / type error | Source app returned a changed field type | Trigger a full refresh for that stream |
| Timeout / cancellation | Stream takes too long to complete | Increase `time_limit_mins` or tune batch size |
| One stream errors, others abandoned | Early failure stops downstream streams | Fix the errored stream; abandoned streams auto-recover |
| `GLOBAL_ERROR` set (no stream-level errors) | Catastrophic failure before streams started | Check connection health; may need support investigation |

---

## Stopping Points

- After Step 1 if the user only needed to identify the sync or check overall inbound health
- After Step 2 if the user wanted run history and freshness trends only
- After Step 3 if the user wants to understand which streams are failing and why
- After Step 4 if the user needs per-stream record counts from the last run
- After Step 5 if the user wants to inspect or reset the stream cursor state
- Offer next steps after Step 3: re-authenticate the connection, trigger a full refresh,
  adjust tuning parameters, or escalate via `references/support-handoff.md`
