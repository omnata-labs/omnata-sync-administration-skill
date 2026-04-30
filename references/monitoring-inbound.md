<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-monitoring-inbound
description: "Monitor and investigate inbound Omnata syncs — syncs that pull data from an external app into Snowflake. Use when: user asks about inbound sync health, data freshness, when data was last synced, which streams failed, stream error messages, stream cursor state, or why inbound data is stale or missing. Also covers normalized view problems: missing views, stale columns, SQL errors on query, access denied, recreating views, refreshing schemas. Triggers: inbound sync, data freshness, last sync time, when was data synced, stream failed, stream error, inbound stream failure, new records, changed records, stream abandoned, stream cancelled, inbound sync error, stream not syncing, normalized view, view missing, view error, schema stale, columns missing, recreate views, refresh schema, access denied inbound."
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
| Schema / type error | Source app returned a changed field type or new field added | Trigger a full refresh for that stream; if the normalized view is also stale or missing columns, follow the **Normalized View Troubleshooting** section below |
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

---

## Normalized View Troubleshooting

<!-- contributor: Co-work — scenario structure, grants checks, UI guidance; Cortex Code — stored procedure signatures and version history -->

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

### NV Step 1: Diagnose the Symptom

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

### NV Step 2: Grants Check (access denied symptom only)

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

### NV Step 3: Fix — Schema Stale (SQL errors, missing or extra columns)

**Option A — Omnata UI:**
1. Navigate to the sync in the Omnata app
2. Go to the **Data** tab
3. Under **Normalized view schemas**, expand **View schema details**
4. Click **Refresh Schemas** — wait for completion
5. Click **Recreate All Views**

**Option B — Stored procedures:**

> ⚠️ These procedures are not documented in the official Omnata gitbook (release notes only).
> Consumer-callable and reliable, but signatures may change between versions.
> `REFRESH_INBOUND_STREAM_SCHEMAS` available since V3.60;
> `RECREATE_INBOUND_NORMALIZED_VIEWS` since V3.17 (`IGNORE_ERRORS` added V3.126).

**Step 1 — Refresh schemas from the source app:**

```sql
CALL OMNATA_SYNC_ENGINE.API.REFRESH_INBOUND_STREAM_SCHEMAS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT()   -- empty = all streams; or ARRAY_CONSTRUCT('issues', 'projects')
);
```

Confirm the returned OBJECT shows `"success": true` before proceeding.

**Step 2 — Recreate normalized views:**

```sql
CALL OMNATA_SYNC_ENGINE.API.RECREATE_INBOUND_NORMALIZED_VIEWS(
    '<sync_slug>',
    'main',
    ARRAY_CONSTRUCT(),  -- empty = all streams; or specific stream names
    TRUE                -- IGNORE_ERRORS: TRUE = skip failures and report them; FALSE = halt on first error
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

### NV Step 4: Fix — View Missing

Check whether the schema is stored — if yes, only recreate is needed:

```sql
CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
    '<sync_slug>',
    'main'
);
```

If the stream appears with a non-empty `view_body` → schema intact, run recreate only.
If the stream is absent or `view_body` is empty → run refresh first, then recreate.

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

### NV Step 5: Verify

```sql
-- Confirm the view is queryable:
SELECT * FROM <database>.<schema>."<view_name>" LIMIT 5;

-- Confirm column count:
SELECT COUNT(*) AS COLUMN_COUNT
FROM <database>.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '<schema>'
  AND TABLE_NAME = '<view_name>';
```

If the view was recreated and the user previously had access, re-check grants — view
recreation drops and rebuilds the object, which removes any direct `SELECT` grants.
Database role grants (managed access schemas) survive recreation and don't need re-applying.

Escalate to `references/support-handoff.md` if `streams_failed` is non-empty after retry
and the error is not self-explanatory.
