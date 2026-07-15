<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-actions
description: "Reference for all Omnata Sync Engine stored procedures and action-based features. Use when: user wants to run, pause, resume, or cancel a sync manually; wants to resync specific records; asks how to configure pre or post hooks; asks what stored procedures are available; needs to set application-level settings, storage locations, or reassign a sync to a different connection. Triggers: run sync, pause sync, resume sync, cancel sync, trigger sync, resync records, pre hook, post hook, before sync, after sync, stored procedures, omnata api, set storage location, reassign connection, app settings, skip record, force resync."
---

# Omnata Sync Engine — Actions Reference

This file documents the full stored procedure interface exposed by `OMNATA_SYNC_ENGINE.API`,
plus the pre/post hook feature for running custom SQL around sync runs. Use it when the user
wants to take an action rather than monitor state.

> **Tip:** Most day-to-day actions (trigger a re-run, pause/resume) are surfaced through the
> monitoring workflow files. This file is the canonical reference for signatures, parameters,
> and advanced usage.

---

## Sync Lifecycle

### Run a Sync

Triggers an immediate sync run. The sync must not already be `RUNNING` and must not be `PAUSED`.

```sql
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(
    NULL,                              -- SYNC_ID (NUMBER)    — set to NULL when using slug
    '<sync_slug>',                     -- SYNC_SLUG (VARCHAR) — from DATA_VIEWS.SYNC
    'main',                            -- BRANCH_NAME (VARCHAR)
    'external',                        -- RUN_SOURCE_NAME (VARCHAR)
    {'triggered_by': 'cortex_code'},   -- RUN_SOURCE_METADATA (OBJECT)
    false                              -- WAIT_FOR_COMPLETION (BOOLEAN)
);
```

| Parameter | Type | Notes |
|---|---|---|
| `SYNC_ID` | NUMBER | Use this **or** `SYNC_SLUG`, not both. Set the unused one to `NULL`. |
| `SYNC_SLUG` | VARCHAR | Preferred — human-readable and unambiguous. From `DATA_VIEWS.SYNC.SYNC_SLUG`. |
| `BRANCH_NAME` | VARCHAR | Always `'main'` unless the sync uses advanced branching mode. |
| `RUN_SOURCE_NAME` | VARCHAR | Label for the trigger origin — use `'external'` for Cortex Code-initiated runs. |
| `RUN_SOURCE_METADATA` | OBJECT | Optional metadata attached to the run — useful for audit trail. |
| `WAIT_FOR_COMPLETION` | BOOLEAN | `false` = async (returns immediately after enqueue). `true` = blocks until run finishes. |

**After triggering,** confirm the run was enqueued by checking the returned OBJECT, then query for the new run:

```sql
SELECT SYNC_RUN_ID, RUN_STATE, HEALTH_STATE, RUN_START_DATETIME
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN
WHERE SYNC_ID = (SELECT SYNC_ID FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_SLUG = '<sync_slug>')
ORDER BY RUN_START_DATETIME DESC
LIMIT 1;
```

---

### Pause a Sync

Suspends the sync schedule. The sync will not run until resumed. Existing in-progress runs are
not cancelled.

```sql
CALL OMNATA_SYNC_ENGINE.API.PAUSE_SYNC(
    NULL,          -- SYNC_ID (NUMBER) — or NULL if using slug
    '<sync_slug>'  -- SYNC_SLUG (VARCHAR)
);
```

---

### Resume a Sync

Re-enables the sync schedule after a pause. Does not immediately trigger a run — the sync will
run at its next scheduled interval.

```sql
CALL OMNATA_SYNC_ENGINE.API.RESUME_SYNC(
    NULL,          -- SYNC_ID (NUMBER) — or NULL if using slug
    '<sync_slug>'  -- SYNC_SLUG (VARCHAR)
);
```

> **If resuming and also triggering immediately:** Call `RESUME_SYNC` first, then `RUN_SYNC`.

---

## Inbound Sync Data Actions

### Refresh Inbound Stream Schemas

Polls the source application to discover new or changed object schemas for the specified inbound
sync. Run this when new fields or objects have been added in the source app and are not yet
visible in Snowflake.

**Minimum version: v3.60**

```sql
CALL OMNATA_SYNC_ENGINE.API.REFRESH_INBOUND_STREAM_SCHEMAS(
    '<sync_slug>',            -- SYNC_SLUG (VARCHAR)
    'main',                   -- BRANCH_NAME (VARCHAR)
    ARRAY_CONSTRUCT()         -- STREAM_NAMES (ARRAY) — empty array = all streams
);
```

To refresh specific streams only:

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

### Recreate Inbound Normalized Views

Rebuilds the normalized views in `INBOUND_NORMALIZED` that flatten the `RECORD_DATA` JSON
column from raw inbound tables. Run this after schema refresh, when views are missing, or when
column definitions are stale.

**Minimum version: v3.17. `IGNORE_ERRORS` parameter added: v3.126**

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

> **Warning:** Recreating views drops and recreates them. Any grants on the views
> (e.g. `SELECT` for downstream roles) must be re-applied after recreation.

---

### Get Inbound View Definitions

Returns the SQL `CREATE VIEW` definitions for all normalized views in an inbound sync.
Use this to inspect what columns each view exposes, or to manually recreate a specific view.

```sql
SELECT * FROM TABLE(
    OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
        '<sync_slug>',
        'main'
    )
);
```

---

## Record-Level Actions

### Resync a Record

To force a specific outbound record to be re-sent to the destination on the next sync run,
update its `APPLY_STATE` in the source table (or using the Omnata UI record management).
Records with `APPLY_STATE = 'RESYNC_REQUESTED'` are re-queued for the next run regardless
of whether they previously succeeded.

> **Note:** Record-level `APPLY_STATE` is managed by Omnata on outbound sync records.
> The `APPLY_STATE` values and their meanings:

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

The recommended way to trigger a resync for one or more records is through the **Omnata UI**
(record management tab). If bulk resync is needed via SQL, this is an advanced operation —
advise the user to contact Omnata support for guidance before modifying `APPLY_STATE` directly.

---

## Connection Actions

> These procedures are **undocumented** in the official Omnata gitbook. They exist and work,
> but may change without notice. Only suggest them when the user explicitly needs to perform
> these operations. Always direct connection creation, editing, and credential management to
> the **Omnata UI** — those operations require Account Admin privileges and cannot be done
> from SQL.

### Delete a Connection

Permanently deletes a connection. **Fails if any syncs still reference it.**

```sql
-- ⚠️ UNDOCUMENTED. Irreversible.
-- SYNC_ID = CONNECTION_ID (FLOAT) — from DATA_VIEWS.CONNECTION
CALL OMNATA_SYNC_ENGINE.API.DELETE_CONNECTION(<connection_id>);
```

Before calling: confirm `TOTAL_SYNCS = 0` for this connection (see monitoring-connections.md
Step 1), or that all syncs have already been deleted or reassigned.

---

### Set Connection Environment

Changes a connection's production/sandbox flags without going through the full UI edit flow.

```sql
-- ⚠️ UNDOCUMENTED.
-- Args: CONNECTION_ID (NUMBER), IS_PRODUCTION (BOOLEAN), IS_SANDBOX (BOOLEAN)
CALL OMNATA_SYNC_ENGINE.API.SET_CONNECTION_ENVIRONMENT(<connection_id>, <is_production>, <is_sandbox>);
```

---

### Reassign a Sync to a Different Connection

Moves a sync (or a specific branch) from one connection to another. Useful when migrating syncs
during a connection consolidation or credential handover.

```sql
-- ⚠️ UNDOCUMENTED.
-- Args appear to be: SYNC_ID (FLOAT), CONNECTION_ID (FLOAT), BRANCH_ID (FLOAT)
CALL OMNATA_SYNC_ENGINE.API.SET_SYNC_CONNECTION(<sync_id>, <connection_id>, <branch_id>);
```

> Get `BRANCH_ID` from `DATA_VIEWS.SYNC_BRANCH` if the table exists, or use `0` for the
> main branch. Verify with Omnata support before running against production syncs.

---

## Application-Level Settings

### Set Default Inbound Storage Location

Configures where inbound sync raw tables and normalized views are created by default. Override
this when you want inbound data in a specific database/schema rather than the Omnata default.

```sql
-- ⚠️ UNDOCUMENTED.
CALL OMNATA_SYNC_ENGINE.API.SET_DEFAULT_INBOUND_STORAGE_LOCATION(
    {
        'database_name': '<target_database>',
        'schema_name': '<target_schema>'
    }
);
```

> **Note:** Changing the default storage location applies to **new** inbound syncs. Existing
> syncs retain their existing storage location. To move an existing sync's data, contact
> Omnata support.

---

### Set Application Setting

Sets an application-level configuration value. Available setting names are not publicly
documented — use only when Omnata support has provided a specific setting name and value.

```sql
-- ⚠️ UNDOCUMENTED. Use only when Omnata support provides specific instructions.
CALL OMNATA_SYNC_ENGINE.API.SET_APP_SETTING('<setting_name>', <value_object>);
```

---

## Pre/Post Hooks

Hooks allow you to run custom SQL before or after each sync run. They are configured per-sync
through the Omnata UI (sync settings → Advanced) and run as part of the sync pipeline, not
as a separate Snowflake task.

### Hook types

| Hook type | When it runs | Typical use |
|---|---|---|
| **Pre-run hook** | Before the sync run starts | Prepare staging tables, snapshot source views, set session parameters |
| **Post-run hook** | After the sync run completes (regardless of success or failure) | Trigger downstream transforms, refresh materialized views, send notifications, log run metadata |

### How hooks are defined

Hooks are configured in the Omnata UI as a SQL statement or a `CALL` to a stored procedure
in your Snowflake account. The hook runs with the privileges of the Omnata application's
execution context.

```sql
-- Example pre-run hook: truncate a staging table before inbound sync
TRUNCATE TABLE MY_DATABASE.STAGING.SALESFORCE_CONTACTS_STAGE;
```

```sql
-- Example post-run hook: call a transformation procedure after inbound sync completes
CALL MY_DATABASE.TRANSFORMS.REFRESH_CONTACT_DIM();
```

### Viewing hook configuration

Hook SQL is stored as sync metadata. To retrieve the current hook configuration for a sync:

```sql
SELECT
    SYNC_ID,
    SYNC_NAME,
    SYNC_DIRECTION,
    SYNC_CONFIGURATION:pre_run_hook::VARCHAR  AS PRE_RUN_HOOK_SQL,
    SYNC_CONFIGURATION:post_run_hook::VARCHAR AS POST_RUN_HOOK_SQL
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_ID = <sync_id>;
```

> **Note:** If `SYNC_CONFIGURATION` does not expose hook SQL in your Omnata version, hook
> configuration is only visible through the Omnata UI (sync settings → Advanced).

### Hook failure behaviour

If a pre-run hook fails, the sync run is aborted and the failure is recorded in
`SYNC_RUN.GLOBAL_ERROR` with a message indicating the hook SQL that failed. If a post-run
hook fails, the sync run is marked as complete but the hook failure is logged. Check
`GLOBAL_ERROR` in `DATA_VIEWS.SYNC_RUN` for hook-related errors.

---

## Quick Reference

| Procedure | Parameters | Notes |
|---|---|---|
| `RUN_SYNC` | `(SYNC_ID, SYNC_SLUG, BRANCH_NAME, SOURCE_NAME, SOURCE_METADATA, WAIT)` | Trigger a run |
| `PAUSE_SYNC` | `(SYNC_ID, SYNC_SLUG)` | Suspend schedule |
| `RESUME_SYNC` | `(SYNC_ID, SYNC_SLUG)` | Re-enable schedule |
| `CONFIGURE_OMNATA_OUTBOUND_SYNC` | 21 positional params — see `references/configure-syncs.md` | Create or update an outbound sync. Idempotent. |
| `CONFIGURE_OMNATA_INBOUND_SYNC` | 28 params (8 required) — see `references/configure-syncs.md` | Create or update an inbound sync with bulk stream setup. Idempotent. |
| `REFRESH_INBOUND_STREAM_SCHEMAS` | `(SYNC_SLUG, BRANCH_NAME, STREAM_NAMES)` | Pull latest schemas from source app. Min v3.60. |
| `RECREATE_INBOUND_NORMALIZED_VIEWS` | `(SYNC_SLUG, BRANCH_NAME, STREAM_NAMES, IGNORE_ERRORS)` | Rebuild normalized views. Min v3.17. |
| `GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS` | `(SYNC_SLUG, BRANCH_NAME)` | Return CREATE VIEW SQL for all streams |
| `DELETE_CONNECTION` | `(CONNECTION_ID)` | ⚠️ Undocumented. Irreversible. |
| `SET_CONNECTION_ENVIRONMENT` | `(CONNECTION_ID, IS_PRODUCTION, IS_SANDBOX)` | ⚠️ Undocumented. |
| `SET_SYNC_CONNECTION` | `(SYNC_ID, CONNECTION_ID, BRANCH_ID)` | ⚠️ Undocumented. Reassign sync to different connection. |
| `SET_DEFAULT_INBOUND_STORAGE_LOCATION` | `(OBJECT)` | ⚠️ Undocumented. Set default inbound schema. |
| `SET_APP_SETTING` | `(SETTING_NAME, VALUE)` | ⚠️ Undocumented. Use only on Omnata support instruction. |
