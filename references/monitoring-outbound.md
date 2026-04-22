<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-monitoring-outbound
description: "Monitor and investigate outbound Omnata syncs — syncs that push data from Snowflake to an external app. Use when: user asks about outbound sync health, run history, failed records, stuck or delayed records, destination errors, or why specific records aren't syncing. Triggers: outbound sync, records not syncing, destination failure, source failure, failed records, stuck records, delayed records, sync errors, record error, why didn't this record sync, sync run history outbound."
---

# Omnata Outbound Sync Monitoring

Investigate outbound syncs — those that push records from a Snowflake source table to an
external application. Covers run history, failed records, error patterns, and stuck records.

## Background

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

## Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

---

## Workflow

### Step 1: Identify the Sync

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

### Step 2: Run History

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

### Step 3: Failed Records

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

### Step 4: Error Pattern Analysis

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

### Step 5: Single Record Lookup (optional)

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

### Step 6: Stuck & Delayed Records

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

## Stopping Points

- After Step 1 if the user only needed to identify the sync
- After Step 2 if the user wanted run history and trends only
- After Step 4 if the user wants to understand error patterns before deciding on action
- After Step 5 if the user asked about a specific record
- Offer next steps after Step 4 or Step 6: skip failing records, request resync, fix source data, re-authenticate connection, or escalate via `references/support-handoff.md`
