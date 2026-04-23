<!-- owner: cortex-code — do not edit if you are not Cortex Code (Snowflake CLI). -->
---
name: omnata-event-table-diagnostics
description: "Deep diagnostic investigation using the Snowflake Event Table to trace Omnata sync failures. Use when: DATA_VIEWS errors need deeper investigation, stack traces are needed, the user wants to understand exactly where a sync failed in the code path, or when GLOBAL_ERROR or INBOUND_GLOBAL_ERROR_BY_STREAM are insufficient to diagnose the root cause. Triggers: event table, event logs, stack trace, deeper investigation, trace sync failure, why did the sync fail, debug sync, diagnose sync."
---

# Omnata Event Table Diagnostics

Omnata Sync Engine is a Snowflake Native Application that emits log, span, and metric
events to the account's Snowflake Event Table. This reference covers how to query those
events to get deeper diagnostic detail than `DATA_VIEWS` provides — full stack traces,
sync run lifecycle timelines, and recurring error patterns.

## When to use this reference

Use this **after** the primary monitoring workflows (`monitoring-sync-status.md`,
`monitoring-outbound.md`, `monitoring-inbound.md`, etc.) have surfaced an error. This reference adds:

- Full Python stack traces (not available in `DATA_VIEWS`)
- The exact code path and function where a sync failed
- A timeline of sync run lifecycle phases (start → staging → syncing → post-processing → complete)
- Recurring error detection across many runs
- Correlation between `DATA_VIEWS` sync runs and event table trace spans

Do **not** start here — always start with `DATA_VIEWS` to identify the failing sync and
run, then come here for deeper investigation.

## Prerequisites

- Active Snowflake connection with a role that can read the account event table
- The event table location varies by account — always discover it dynamically (Step 0)
- The Omnata app install name is usually `OMNATA_SYNC_ENGINE` (the default), but users
  can choose a custom name during installation — always discover it dynamically (Step 1)
- Event tables are regular Snowflake tables — data persists until explicitly deleted or
  truncated. There is no automatic expiry. However, if the event table was recently
  configured, or has been manually purged, historical data may not be available. Always
  check the earliest available timestamp (Step 2) before searching for a specific run.

## Workflow

### Step 0: Discover the Event Table

The event table name is account-specific. Always discover it first:

```sql
SHOW PARAMETERS LIKE 'EVENT_TABLE' IN ACCOUNT
```

The result column `value` contains the fully qualified table name (e.g.
`my_db.my_schema.my_event_table`). Use this value in all subsequent queries.

If the value is empty, no event table is configured and diagnostics are not available —
report this to the user and stop.

If the value is `SNOWFLAKE.TELEMETRY.EVENTS`, the account is using Snowflake's default
event table. This is fully valid — use it for all subsequent queries. Note that querying
this table requires the `EVENTS_VIEWER` or `EVENTS_ADMIN` application role (granted by
`ACCOUNTADMIN`). If the user gets a permissions error, they should request access from
their Snowflake account admin.

### Step 1: Discover the Omnata Application Name

The default Omnata install database name is `OMNATA_SYNC_ENGINE` and most accounts use
this default. However, users can choose a custom name during installation (e.g.
`OMNATA_APP_JAMES`). The `snow.application.name` resource attribute in the event table
matches the install database name. Discover it:

```sql
SELECT
    RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR AS APP_NAME,
    COUNT(*) AS EVENT_COUNT
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR ILIKE 'OMNATA%'
  AND RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR NOT ILIKE 'OMNATA_TEST%'
GROUP BY 1
ORDER BY 2 DESC
```

This returns all Omnata app installations on the account. Use the correct app name
(referred to as `<omnata_app_name>` in all subsequent queries) for the installation
you are diagnosing. If the user told you the install database name, confirm it appears
in this list.

If multiple app names appear, ask the user which installation to diagnose.

> **Note:** Connector plugin apps (e.g. `OMNATA_SALESFORCE_PLUGIN`, `OMNATA_HUBSPOT_PLUGIN`) always contain `PLUGIN` in their name. They emit their own events to the same event table under their own app name. The workflows in this file focus on `OMNATA_SYNC_ENGINE` events. For plugin-level events (credential updates, API configuration, connection tests), filter on `ILIKE '%PLUGIN%'` — see "Step 4b: Secret and credential update events" in `references/monitoring-connections.md`.

### Step 2: Verify Omnata Events Exist

Before running detailed queries, confirm events from the target Omnata app are present:

```sql
SELECT RECORD_TYPE, COUNT(*) AS EVENT_COUNT
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
GROUP BY 1
ORDER BY 2 DESC
```

Expected record types:

| Record Type | What it contains |
|---|---|
| `LOG` | Application log messages at various severity levels |
| `SPAN` | OpenTelemetry trace spans covering sync run lifecycle phases |
| `SPAN_EVENT` | Named milestone events within spans (sync start, complete, etc.) |
| `METRIC` | CPU and memory usage per procedure execution |

If no rows are returned, event sharing may not be configured or the event table may have
been recently rotated. Report this and stop.

Also check the earliest available data — event tables retain data indefinitely until
explicitly deleted or truncated, but the table may be new or may have been manually purged:

```sql
SELECT MIN(TIMESTAMP) AS EARLIEST_EVENT, MAX(TIMESTAMP) AS LATEST_EVENT
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE IN ('SPAN', 'SPAN_EVENT')
```

If the target sync run's timestamp is earlier than `EARLIEST_EVENT`, data for that run
is not available — inform the user and suggest investigating a more recent failed run instead.

### Step 3: Find the Trace for a Specific Sync Run

Given a `SYNC_RUN_ID` from `DATA_VIEWS.SYNC_RUN`, find the corresponding trace spans:

```sql
SELECT
    TIMESTAMP,
    RECORD_TYPE,
    RECORD:name::VARCHAR                                    AS SPAN_NAME,
    RECORD_ATTRIBUTES:"omnata.sync_run.id"::INTEGER         AS SYNC_RUN_ID,
    RECORD_ATTRIBUTES:"omnata.sync.id"::INTEGER             AS SYNC_ID,
    RECORD_ATTRIBUTES:"omnata.sync.slug"::VARCHAR           AS SYNC_SLUG,
    RECORD_ATTRIBUTES:"omnata.sync.direction"::VARCHAR      AS SYNC_DIRECTION,
    RECORD_ATTRIBUTES:"omnata.sync_branch.name"::VARCHAR    AS SYNC_BRANCH,
    TRACE:trace_id::VARCHAR                                 AS TRACE_ID,
    TRACE:span_id::VARCHAR                                  AS SPAN_ID,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE IN ('SPAN', 'SPAN_EVENT')
  AND RECORD_ATTRIBUTES:"omnata.sync_run.id"::INTEGER = <sync_run_id>
ORDER BY TIMESTAMP
```

This returns the `TRACE_ID` which links all events (LOG, SPAN, SPAN_EVENT, METRIC) from
the same procedure execution. A single sync run may have up to three trace IDs:
- `RUN_SYNC` — the orchestrator that validates and enqueues the run
- `PROCESS_SYNC_RUN` — the worker that executes the sync
- `PROCESS_SYNC_RUN_BACKGROUND` — background worker for inbound syncs

Note: `omnata.sync_run.id` is only set on SPAN records (not SPAN_EVENT), and the SPAN
is emitted at the END of procedure execution. If the run is still in progress or the
event hasn't been flushed yet, try the time-window search below instead.

If no results are found for the `SYNC_RUN_ID`, try matching by sync slug instead:

```sql
SELECT
    TIMESTAMP,
    RECORD_TYPE,
    RECORD:name::VARCHAR                                AS SPAN_NAME,
    RECORD_ATTRIBUTES:"omnata.sync_run.id"::INTEGER     AS SYNC_RUN_ID,
    RECORD_ATTRIBUTES:"omnata.sync.slug"::VARCHAR       AS SYNC_SLUG,
    TRACE:trace_id::VARCHAR                             AS TRACE_ID,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR AS EXECUTABLE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE IN ('SPAN', 'SPAN_EVENT')
  AND RECORD_ATTRIBUTES:"omnata.sync.slug"::VARCHAR = '<sync_slug>'
  AND TIMESTAMP BETWEEN '<run_start_minus_5min>' AND '<run_end_plus_5min>'
ORDER BY TIMESTAMP
```

### Step 4: Get ERROR and WARNING Logs for the Trace

Using the `TRACE_ID` from Step 3, pull all error and warning logs:

```sql
SELECT
    TIMESTAMP,
    RECORD:severity_text::VARCHAR                           AS SEVERITY,
    SCOPE:name::VARCHAR                                     AS SCOPE_NAME,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE,
    RECORD_ATTRIBUTES:"exception.type"::VARCHAR             AS EXCEPTION_TYPE,
    RECORD_ATTRIBUTES:"exception.message"::VARCHAR          AS EXCEPTION_MESSAGE,
    RECORD_ATTRIBUTES:"exception.stacktrace"::VARCHAR       AS STACKTRACE,
    RECORD_ATTRIBUTES:"code.filepath"::VARCHAR              AS CODE_FILE,
    RECORD_ATTRIBUTES:"code.function"::VARCHAR              AS CODE_FUNCTION,
    RECORD_ATTRIBUTES:"code.lineno"::INTEGER                AS CODE_LINE,
    VALUE::VARCHAR                                          AS LOG_MESSAGE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE = 'LOG'
  AND RECORD:severity_number >= 13  -- WARN (13) and above: WARN, ERROR, FATAL
  AND TRACE:trace_id::VARCHAR = '<trace_id>'
ORDER BY TIMESTAMP
```

**Key fields to present:**
- `EXCEPTION_TYPE` — the Python exception class (e.g. `ValueError`, `KeyError`)
- `EXCEPTION_MESSAGE` — the human-readable error message
- `STACKTRACE` — the full Python traceback showing the code path to the failure
- `CODE_FILE` / `CODE_FUNCTION` / `CODE_LINE` — the exact source location

If the trace has no ERROR/WARN logs, expand to include INFO to see how far the run got:

```sql
SELECT
    TIMESTAMP,
    RECORD:severity_text::VARCHAR   AS SEVERITY,
    SCOPE:name::VARCHAR             AS SCOPE_NAME,
    VALUE::VARCHAR                  AS LOG_MESSAGE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE = 'LOG'
  AND RECORD:severity_text::VARCHAR != 'DEBUG'
  AND TRACE:trace_id::VARCHAR = '<trace_id>'
ORDER BY TIMESTAMP
```

### Step 5: Get the Sync Run Lifecycle Timeline

For a complete picture of what the sync run did before failing, pull the SPAN_EVENT
milestones:

```sql
SELECT
    TIMESTAMP,
    RECORD:name::VARCHAR        AS EVENT_NAME,
    RECORD_ATTRIBUTES           AS EVENT_ATTRIBUTES
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE = 'SPAN_EVENT'
  AND TRACE:trace_id::VARCHAR IN ('<run_sync_trace_id>', '<process_sync_run_trace_id>', '<process_sync_run_background_trace_id>')
ORDER BY TIMESTAMP
```

Omnata emits these lifecycle milestones (in order for a healthy **outbound** run):

1. `sync_run_start` — run initiated
2. `sync_run_enqueued` — queued for the worker process
3. `sync_run_processing` — worker picked it up
4. `sync_run_outbound_staging` — staging source records
5. `sync_run_outbound_preparing` — transforming and batching
6. `sync_run_syncing` — sending to destination
7. `sync_run_outbound_post_processing` — updating record states
8. `sync_run_complete` — finished (includes `omnata.run_health_state` and apply state counts)

For a healthy **inbound** run, the lifecycle milestones are:

1. `sync_run_start` — run initiated
2. `sync_run_enqueued` — queued for the worker process
3. `sync_run_inbound_checking_new_streams` — checking for new data streams
4. `sync_run_processing` — worker picked it up
5. `sync_run_syncing` — pulling data from source
6. `sync_run_inbound_post_processing` — processing received data
7. `sync_run_inbound_refreshing_schemas` — refreshing destination schemas
8. `sync_run_inbound_reading_schemas` — reading updated schema information
9. `sync_run_inbound_maintaining_normalized_views` — updating normalized views
10. `sync_run_complete` — finished (includes `omnata.run_health_state`)

If the run failed, the timeline will stop at the phase where the error occurred — this
tells you whether the failure was during initialization, staging, syncing, or post-processing.

The `sync_run_complete` event (when present) includes outbound apply state counts as
attributes:
- `omnata.outbound_apply_state_counts.SUCCESS`
- `omnata.outbound_apply_state_counts.DESTINATION_FAILURE`
- `omnata.outbound_total_count`
- `omnata.run_health_state`

### Step 6: Search for Recurring Errors (Optional)

To check if an error is a one-off or a persistent pattern across runs:

```sql
SELECT
    TIMESTAMP::DATE                                         AS ERROR_DATE,
    RECORD_ATTRIBUTES:"exception.type"::VARCHAR             AS EXCEPTION_TYPE,
    RECORD_ATTRIBUTES:"exception.message"::VARCHAR          AS EXCEPTION_MESSAGE,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE,
    COUNT(*) OVER (PARTITION BY RECORD_ATTRIBUTES:"exception.message"::VARCHAR) AS TOTAL_OCCURRENCES
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE = 'LOG'
  AND RECORD:severity_number >= 17  -- ERROR and above
  AND TIMESTAMP >= DATEADD('day', -30, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC
LIMIT 50
```

This helps distinguish:
- **Persistent errors** — same exception message recurring daily (e.g. a deleted sync
  still being triggered by a stale Snowflake task)
- **Intermittent errors** — occasional failures mixed with successes (e.g. rate limiting,
  transient network issues)
- **One-off errors** — a single failure that hasn't recurred (e.g. a temporary config change)

### Step 7: Search by Error Text (Optional)

When you have an error message from `DATA_VIEWS` (e.g. `GLOBAL_ERROR` or `LAST_RESULT`)
and want the event table's stack trace for it:

```sql
SELECT
    TIMESTAMP,
    RECORD:severity_text::VARCHAR                           AS SEVERITY,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE,
    RECORD_ATTRIBUTES:"exception.type"::VARCHAR             AS EXCEPTION_TYPE,
    RECORD_ATTRIBUTES:"exception.message"::VARCHAR          AS EXCEPTION_MESSAGE,
    RECORD_ATTRIBUTES:"exception.stacktrace"::VARCHAR       AS STACKTRACE,
    TRACE:trace_id::VARCHAR                                 AS TRACE_ID
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RECORD_TYPE = 'LOG'
  AND RECORD:severity_number >= 17
  AND VALUE::VARCHAR ILIKE '%<error_text_fragment>%'
ORDER BY TIMESTAMP DESC
LIMIT 10
```

Use a distinctive fragment from the `GLOBAL_ERROR` or `LAST_RESULT` message — this avoids
needing to know the trace ID upfront.

**Important:** Some errors (especially inbound stream configuration errors) are logged by
`CONFIGURE_OMNATA_INBOUND_SYNC(...)` rather than the sync run procedures (`RUN_SYNC` /
`PROCESS_SYNC_RUN`). If you cannot find an error in the sync run's trace, use this
text-search approach to find it regardless of which procedure logged it.

## Omnata Event Table Schema Reference

### Resource Attributes (on all Omnata events)

| Attribute | Description |
|---|---|
| `snow.application.name` | The Omnata install database name (varies per account — e.g. `OMNATA_SYNC_ENGINE`, `OMNATA_APP_JAMES`). Use as the primary filter. |
| `snow.executable.name` | The procedure name (e.g. `RUN_SYNC(...)`, `PROCESS_SYNC_RUN(...)`) |
| `snow.executable.type` | `PROCEDURE` or `STREAMLIT` (for Admin UI events) |
| `snow.schema.name` | `API` for sync procedures, `UI` for the admin Streamlit app |
| `snow.query.id` | The Snowflake query ID for the procedure execution |
| `snow.warehouse.name` | Which warehouse executed the procedure |
| `snow.patch` | The Omnata app version (patch number) |

### Omnata-specific Attributes (on SPAN and SPAN_EVENT records)

| Attribute | Found on | Description |
|---|---|---|
| `omnata.sync.id` | `RUN_SYNC` spans | The sync ID — joins to `SYNC.SYNC_ID` |
| `omnata.sync.slug` | `RUN_SYNC` spans | The sync slug |
| `omnata.sync.direction` | `RUN_SYNC` spans | `outbound` or `inbound` |
| `omnata.sync_branch.name` | `RUN_SYNC` spans | Branch name (`main` or custom) |
| `omnata.sync_run.id` | `PROCESS_SYNC_RUN` spans | The run ID — joins to `SYNC_RUN.SYNC_RUN_ID` |
| `omnata.run_health_state` | `sync_run_complete` events | Final health state of the run |
| `omnata.outbound_total_count` | `sync_run_complete` events | Total records processed |
| `omnata.outbound_apply_state_counts.*` | `sync_run_complete` events | Per-state record counts |

### Log Severity Levels

| severity_number | severity_text | Use |
|---|---|---|
| 5 | DEBUG | Internal connector/driver debug output (very high volume, skip) |
| 9 | INFO | Normal operational messages |
| 13 | WARN | Warnings that may indicate issues |
| 17 | ERROR | Exceptions and failures |
| 21 | FATAL | Catastrophic failures (rare) |

Filter by `RECORD:severity_number >= 13` to get WARN and above. Exclude DEBUG in all
queries — it contains high-volume Snowflake connector internals.

### Key Procedures

| Executable | Role |
|---|---|
| `RUN_SYNC(...)` | Orchestrator — validates the sync, enqueues the run |
| `PROCESS_SYNC_RUN(...)` | Worker — executes the actual sync (staging, syncing, post-processing) |
| `PROCESS_SYNC_RUN_BACKGROUND(...)` | Background worker — handles inbound sync processing asynchronously |
| `CONFIGURE_OMNATA_INBOUND_SYNC(...)` | Inbound configuration — sets up inbound streams via the API (not used when syncs are created through the UI); errors here indicate stream-level permission or config failures |
| `CREATE_DAILY_BILLING_EVENTS()` | Billing event generation (runs daily) |
| `APPLY_RECORD_HISTORY_RETENTION()` | Housekeeping — trims old record state history |
| `Admin UI` (STREAMLIT) | The Omnata admin Streamlit interface |

## Presenting Results

When presenting event table findings:

1. Show the **timeline** of how far the sync got before failing (which lifecycle phase)
2. Show the **exception type and message** in plain language
3. Show the **stack trace** — focus on the last 2-3 frames which identify the failing function
4. Note whether the error is **recurring** (same message across multiple dates) or one-off
5. Correlate back to the `DATA_VIEWS` error — the event table error message typically
   matches the `GLOBAL_ERROR` or `INBOUND_GLOBAL_ERROR_BY_STREAM` text

After presenting the event table findings, read `references/error-knowledge-base.md`
to classify the error by origin and recommend Omnata-specific remediation actions.

## Stopping Points

- After Step 2 if the event table has no Omnata events (nothing more to do)
- After Step 4 if the stack trace clearly explains the failure
- After Step 5 if the user wants to understand the sync run lifecycle
- After Step 6 if the user needs to know whether this is a persistent or one-off issue
