---
name: omnata-actions
description: "Reference for all Omnata Sync Engine stored procedures and action-based features. Use when: user wants to run, pause, resume, rename or reschedule a sync; wants to resync or skip specific records; wants a full refresh of inbound streams; asks how to set up pre or post run hooks; asks what stored procedures are available; needs to set application-level settings, storage locations, or reassign a sync to a different connection. Triggers: run sync, pause sync, resume sync, trigger sync, rename sync, change schedule, set sync owner, resync records, skip record, force resync, mark records, full refresh, truncate and reload, move inbound tables, pre hook, post hook, SYNC_RUN_PRE_HOOK, SYNC_RUN_POST_HOOK, before sync, after sync, stored procedures, omnata api, set storage location, reassign connection, app settings, cancel sync run."
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

Triggers a sync run for main or a branch.

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

```sql
CALL OMNATA_SYNC_ENGINE.API.PAUSE_SYNC(
    '<sync_slug>',  -- SYNC_SLUG (VARCHAR)
    'main'          -- BRANCH_NAME (VARCHAR) — 'main' (or NULL), or a branch name
);
```

---

### Resume a Sync

Re-enables a paused sync or branch and resumes its scheduler task. It doesn't trigger a run; the sync runs at its next scheduled time. If it isn't paused, it returns `wasAlreadyResumed: true`.

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

**Change a sync's slug** with `SET_SYNC_SLUG(<sync_id>, '<new_slug>')`. Use with caution: external tools such as dbt, and `RUN_SYNC` calls in scheduled jobs, may still use the old slug.

---

### Delete a Sync

Permanently deletes a sync. Irreversible. **For inbound syncs, its raw tables and normalized views are deleted with it**, so the synced data is gone. Before calling, show the user the sync's name and slug, and for inbound syncs the tables and views that will go, and confirm the data isn't needed. Offer to copy it out first (below).

```sql
CALL OMNATA_SYNC_ENGINE.API.DELETE_SYNC(
    '<sync_slug>',  -- SYNC_SLUG (VARCHAR)
    NULL            -- SYNC_ID (NUMBER) — or NULL if using slug
);
```

Returns `{"success": true, "data": {"deleted": true}}`. One call removes:
- the sync record and its configuration
- its raw tables in `OMNATA_SYNC_ENGINE.INBOUND_RAW` (inbound)
- its normalized views in `OMNATA_SYNC_ENGINE.INBOUND_NORMALIZED` (inbound)

The connection and any other syncs on it are untouched. Synced data goes with the raw tables, so if the user wants to keep it, copy it out first (e.g. `CREATE TABLE ... AS SELECT * FROM <normalized view>`).

---

### Clean Up Syncs and Connections

Use this to remove test setups, or a connection and everything on it. Always list what will be deleted and get the user's confirmation before deleting anything.

1. **List the syncs on the connection:**
   ```sql
   SELECT S.SYNC_ID, S.SYNC_SLUG, S.SYNC_NAME, S.SYNC_DIRECTION
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
   JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C ON C.CONNECTION_ID = S.CONNECTION_ID
   WHERE C.CONNECTION_SLUG = '<connection_slug>';
   ```
2. **Show the user the syncs and the connection, and confirm.** Mention that inbound data is deleted with each sync.
3. **Delete each sync** with `DELETE_SYNC` (above).
4. **Delete the connection** with `DELETE_CONNECTION` (see Connection Actions). It fails while any sync still references it.
5. **Confirm** the connection and syncs no longer appear in `DATA_VIEWS.CONNECTION` and `DATA_VIEWS.SYNC`.
6. **Local secrets.** If the connection was created with the secure secret path, offer `cortex secret delete <key>` for each stored secret.

**Everything for a plugin.** Only when the user asks to remove all of a plugin's syncs and connections, for example before uninstalling it:
1. List every sync and connection for the plugin (`DATA_VIEWS.SYNC` and `DATA_VIEWS.CONNECTION` filtered on `PLUGIN_FQN`), with the inbound tables that will go.
2. Show the full list and get the user's explicit confirmation.
3. Call `DELETE_ALL_SYNCS('<PLUGIN_FQN>')`, then `DELETE_ALL_CONNECTIONS('<PLUGIN_FQN>')`.
4. Confirm nothing for the plugin remains in either view.

To abandon a connection that was never completed, use `CANCEL_CONNECTION_CREATION` instead (see `references/configure-connections.md`).

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

Returns the `CREATE VIEW` definitions for all normalized views in an inbound sync, as an OBJECT. Use it to inspect the columns each view exposes, or to create the views yourself (e.g. in dbt).

```sql
CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_ALL_STREAMS_VIEW_DEFINITIONS(
    '<sync_slug>',
    'main'
);
```

For one stream: `CALL OMNATA_SYNC_ENGINE.API.GET_INBOUND_STREAM_VIEW_DEFINITION('<sync_slug>', 'main', '<stream_name>', false)`.

---

### Full Refresh of Inbound Streams

Marks streams so the **next run** re-reads them in full. `TRUNCATE = true` empties the raw tables first; `false` keeps existing rows and merges over them.

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_STREAMS_FOR_FULL_REFRESH(
    <sync_id>,                              -- SYNC_ID (FLOAT)
    'main',                                 -- BRANCH_NAME (VARCHAR)
    ARRAY_CONSTRUCT('Account', 'Contact'),  -- STREAMS (ARRAY)
    false                                   -- TRUNCATE (BOOLEAN)
);
```

- Undo before the next run with `UNMARK_STREAMS_FOR_FULL_REFRESH(<sync_id>, 'main', ARRAY_CONSTRUCT(...))`.
- For a regular full refresh, set a schedule. It's checked at each run and doesn't add extra runs:
  ```sql
  CALL OMNATA_SYNC_ENGINE.API.SET_FULL_REFRESH_SCHEDULE(
      '<sync_slug>', 'main',
      OBJECT_CONSTRUCT('frequency', '0 0 * * 0 UTC', 'frequency_name', 'Weekly', 'truncate_inbound', false)
  );
  ```
  `frequency_name` is one of `Always`, `Daily`, `Weekly`, `Monthly nth day`, `Monthly last day`, `Monthly nth weekday`, `Monthly last weekday`, `Custom`.
- `MARK_PLUGIN_FOR_FULL_REFRESH('<PLUGIN_FQN>', <truncate>)` marks **every stream of every sync and branch** for a plugin. The next runs re-read everything, which uses warehouse credits and the source app's API rate limits, and with `truncate = true` empties the tables first. List the affected syncs and branches for the user and confirm before using it.

---

### Move an Inbound Sync's Tables

Changes where an existing inbound sync's raw tables and normalized views live, **and moves the existing tables and views** to the new location. Changing the default storage location doesn't do this.

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

### Clean Up Orphaned Inbound Objects

Lists or drops inbound tables or views in the Sync Engine's database that no longer belong to any sync. Always run with `LIST_ONLY = true` first and check the list with the user.

```sql
CALL OMNATA_SYNC_ENGINE.API.CLEANUP_INBOUND_OBJECTS('table', true);  -- OBJECT_TYPE 'table' or 'view'; LIST_ONLY
```

---

### Override Inbound Stream State

`SET_INBOUND_SYNC_STATE('<sync_slug>', '<stream_name>', <state_object>)`, or `SET_INBOUND_SYNC_STATE('<sync_slug>', <streams_state_object>)` keyed by stream name, overwrites the stored cursor state. **Only under the direction of Omnata support**: plugins maintain their own state, and a wrong state can skip or duplicate data.

---

## Record-Level Actions

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

### Resync Records

Queues records to be sent again on the next run, whether or not they previously succeeded.

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_RECORDS_FOR_RESYNC(
    '<sync_slug>',                                 -- SYNC_SLUG
    'main',                                        -- BRANCH_NAME
    NULL,                                          -- SYNC_ACTION — optional, e.g. 'Create'; must be valid for the sync's strategy
    ARRAY_CONSTRUCT('<record_id>', '<record_id>')  -- RECORD_IDS — values of the source table's ID column
);
```

### Skip Records

```sql
CALL OMNATA_SYNC_ENGINE.API.MARK_RECORDS_FOR_SKIP(
    '<sync_slug>', 'main',
    'SKIPPED_ONCE',                    -- or 'SKIPPED_ALWAYS'
    ARRAY_CONSTRUCT('<record_id>')
);
```

### Bulk: by criteria

`MARK_MATCHING_RECORDS_FOR_RESYNC(sync_slug, branch_name, sync_action, criteria)`, `MARK_MATCHING_RECORDS_FOR_SKIP(sync_slug, branch_name, apply_state, criteria)` and `MARK_MATCHING_RECORDS_AS_SUCCESSFUL(sync_slug, branch_name, criteria)` act on every record that matches `criteria`, an OBJECT with any of:
- `apply_statuses`: array of `APPLY_STATE` values, e.g. `['DESTINATION_FAILURE']`
- `record_states`: array of record states
- `sync_actions`: array of sync actions
- `search_terms`: array of strings matched against the transformed record

```sql
-- Example: resync every record that failed at the destination
CALL OMNATA_SYNC_ENGINE.API.MARK_MATCHING_RECORDS_FOR_RESYNC(
    '<sync_slug>', 'main', NULL,
    OBJECT_CONSTRUCT('apply_statuses', ARRAY_CONSTRUCT('DESTINATION_FAILURE'))
);
```

Before a bulk call, count the matching records in `DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE` and confirm with the user. `MARK_MATCHING_RECORDS_AS_SUCCESSFUL` stops Omnata retrying those records; use it only when the user is sure they're already correct in the destination.

---

## Connection Actions

> These procedures are **undocumented** in the official Omnata gitbook. They exist and work,
> but may change without notice. Only suggest them when the user explicitly needs to perform
> these operations. To create a connection, use `references/configure-connections.md`.
> To edit credentials or re-authenticate an existing connection, see "Edit an existing connection" in `references/configure-connections.md`.

### Delete a Connection

Permanently deletes a connection. **Irreversible.** It fails if any syncs still reference it. Show the user the connection's name and ID, and confirm before calling it.

```sql
-- ⚠️ UNDOCUMENTED. Irreversible.
-- SYNC_ID = CONNECTION_ID (FLOAT) — from DATA_VIEWS.CONNECTION
CALL OMNATA_SYNC_ENGINE.API.DELETE_CONNECTION(<connection_id>);
```

Before calling: confirm `TOTAL_SYNCS = 0` for this connection (see monitoring-connections.md
Step 1), or that all syncs have already been deleted or reassigned.

---

### Set Connection Environment

Changes whether a connection is production or non-production, without an edit session. See `references/branching.md` for what the flag controls.

```sql
-- ⚠️ UNDOCUMENTED.
CALL OMNATA_SYNC_ENGINE.API.SET_CONNECTION_ENVIRONMENT(<connection_id>, <is_production_environment>);
```

---

### Reassign a Sync to a Different Connection

Moves a sync's main, or one branch, to another connection of the **same plugin**. Useful when consolidating connections or handing over credentials.

```sql
-- ⚠️ UNDOCUMENTED.
CALL OMNATA_SYNC_ENGINE.API.SET_SYNC_CONNECTION(
    <sync_id>,          -- SYNC_ID
    <connection_id>,    -- CONNECTION_ID
    NULL                -- SYNC_BRANCH_ID — NULL for main, or the branch's ID from DATA_VIEWS.SYNC_BRANCH
);
```

- The connection must be for the same plugin as the sync.
- For main, a branched sync can't be moved to a non-production connection.
- Confirm with the user before reassigning a production sync.

---

## Application-Level Settings

### Set Default Inbound Storage Location

Configures where inbound sync raw tables and normalized views are created by default (the same
setting as Settings > Data Management). It takes the same keys as `INBOUND_STORAGE_LOCATION`
(`raw_database`, `raw_schema`, `raw_object`, `normalized_database`, `normalized_schema`,
`normalized_object`, `normalized_column`). Design and preview the template with
`references/data-management.md` before calling it.

```sql
CALL OMNATA_SYNC_ENGINE.API.SET_DEFAULT_INBOUND_STORAGE_LOCATION(
    OBJECT_CONSTRUCT(
        'raw_database',        '<raw_database>',
        'raw_schema',          '<raw_schema>',
        'normalized_database', '<normalized_database>',
        'normalized_schema',   '<normalized_schema>'
    )
);
```

> **Note:** Changing the default applies to **new** syncs created in the UI. Existing syncs keep
> their stored location. `CONFIGURE_OMNATA_INBOUND_SYNC` does not read the default, so pass it
> explicitly as `INBOUND_STORAGE_LOCATION`. To move an existing sync's tables, use
> `SET_INBOUND_SYNC_LOCATION` (see "Move an Inbound Sync's Tables").

---

### Set Application Setting

Sets an application-level configuration value. Available setting names are not publicly
documented — use only when Omnata support has provided a specific setting name and value.

```sql
-- ⚠️ UNDOCUMENTED. Use only when Omnata support provides specific instructions.
CALL OMNATA_SYNC_ENGINE.API.SET_APP_SETTING('<setting_name>', <value_object>);
```

---

## Pre/Post Run Hooks

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
  IF (:RESULT:sync_slug::VARCHAR <> 'contacts-to-salesforce') THEN
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

## Quick Reference

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
| `SET_INBOUND_SYNC_STATE` | `(SYNC_SLUG, STREAM_NAME, STREAM_STATE)` or `(SYNC_SLUG, STREAMS_STATE)` | Support use only |
| `MARK_RECORDS_FOR_RESYNC` | `(SYNC_SLUG, BRANCH_NAME, SYNC_ACTION, RECORD_IDS)` | Outbound only |
| `MARK_RECORDS_FOR_SKIP` | `(SYNC_SLUG, BRANCH_NAME, APPLY_STATE, RECORD_IDS)` | `SKIPPED_ONCE` or `SKIPPED_ALWAYS` |
| `MARK_MATCHING_RECORDS_FOR_RESYNC` / `_FOR_SKIP` / `_AS_SUCCESSFUL` | `(SYNC_SLUG, BRANCH_NAME, [SYNC_ACTION or APPLY_STATE,] CRITERIA)` | Bulk, by criteria |
| `DELETE_CONNECTION` | `(CONNECTION_ID)` | ⚠️ Undocumented. Irreversible. |
| `BEGIN_CONNECTION_CREATION`, `BEGIN_CONNECTION_EDIT`, `UPDATE_CONNECTION_OBJECTS`, `COMPLETE_CONNECTION_CREATION`, `CANCEL_CONNECTION_CREATION` | see `references/configure-connections.md` | Create or edit a connection |
| `SET_CONNECTION_ENVIRONMENT` | `(CONNECTION_ID, IS_PRODUCTION_ENVIRONMENT)` | ⚠️ Undocumented. |
| `SET_SYNC_CONNECTION` | `(SYNC_ID, CONNECTION_ID, SYNC_BRANCH_ID)` | ⚠️ Undocumented. `SYNC_BRANCH_ID` NULL for main |
| `SET_DEFAULT_INBOUND_STORAGE_LOCATION` | `(OBJECT)` | Default for new syncs. See `references/data-management.md` |
| `SET_APP_SETTING` | `(SETTING_NAME, SETTING_VALUE)` | ⚠️ Undocumented. Use only on Omnata support instruction. |
| `DELETE_ALL_SYNCS` / `DELETE_ALL_CONNECTIONS` | `(PLUGIN_FQN)` | **Deletes every sync (with its tables and views) or every connection for a plugin. Irreversible.** Use only through the "Clean Up Syncs and Connections" workflow above: list everything affected and get the user's explicit confirmation first |
