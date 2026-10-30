---
name: omnata-connection-management
description: "Monitor and manage Omnata connections: health, the syncs on each connection, history and credential changes, orphaned connections. Can change things, always after the user confirms: permanently delete a connection (DELETE_CONNECTION), change its production flag (SET_CONNECTION_ENVIRONMENT), move a sync to another connection (SET_SYNC_CONNECTION), and clean up a connection with its syncs (DELETE_SYNC) or every sync and connection for a plugin (DELETE_ALL_SYNCS, DELETE_ALL_CONNECTIONS). To create or edit one, use configure-connections.md. Use when: user asks what Omnata connections exist, which syncs use them, connection health, credential changes, or wants to delete, re-flag or clean up an Omnata connection. Triggers: omnata connections, omnata connection health, orphaned omnata connection, delete omnata connection, clean up omnata test connection, DELETE_CONNECTION, SET_CONNECTION_ENVIRONMENT, SET_SYNC_CONNECTION, DELETE_ALL_SYNCS, DELETE_ALL_CONNECTIONS."
---

# Omnata Connection Management

Check Omnata connections and the syncs that use them (Part 1), then act on them (Part 2). To create or edit a connection, including rotating credentials, use `references/configure-connections.md`.

## Changes this reference can make

Part 1 only reads: `OMNATA_SYNC_ENGINE.DATA_VIEWS` and, for connection errors, the account event table. Part 2 changes things, and each action needs the user's confirmation first:
- **Delete a connection** (`DELETE_CONNECTION`). Irreversible
- **Change its production flag** (`SET_CONNECTION_ENVIRONMENT`)
- **Move a sync to another connection** (`SET_SYNC_CONNECTION`)
- **Clean up** a connection with all its syncs, or everything for a plugin (`DELETE_SYNC`, `DELETE_ALL_SYNCS`, `DELETE_ALL_CONNECTIONS`)

## Part 1: Connection health and history

List all configured connections, their associated syncs, and flag any issues.

### Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

### Creating and editing connections

Users can create connections either in the **Omnata UI** or with **CoCo**.

- **To create a connection with CoCo**, read `references/configure-connections.md` and follow it. It covers API key, token, service account and OAuth methods, from `BEGIN_CONNECTION_CREATION` through to a tested connection.
- **To edit an existing connection with CoCo** (rotate credentials, change connection parameters, rename, change the production flag, re-authorize OAuth), follow "Edit an existing connection" in `references/configure-connections.md`. The Omnata UI can also do this.
- **To test a connection**: there is no test-connection procedure available to customer roles. `COMPLETE_CONNECTION_CREATION` runs the plugin's connection test when a connection is created. For an existing connection, assess health from recent sync runs (Step 3 below).

**Do NOT:**
- Call `TEST_CONNECTION`. It exists but isn't granted to customer roles.
- Create External Access Integrations, Security Integrations, Network Rules or Secrets by hand for an Omnata connection. The plugin creates and owns them during `BEGIN_CONNECTION_CREATION` and `UPDATE_CONNECTION_OBJECTS`.
- Ask the user to paste a credential into the chat. Use the template or secure options in `configure-connections.md`.

### Workflow

#### Step 1: All Connections with Sync Summary

**Goal:** Show every connection with the count and health of its associated syncs.

**Execute:**

```sql
SELECT
    C.CONNECTION_ID,
    C.CONNECTION_NAME,
    SPLIT_PART(C.PLUGIN_FQN, '__', 2)   AS APP,
    C.CONNECTION_METHOD,
    C.IS_PRODUCTION_ENVIRONMENT         AS IS_PRODUCTION,
    C.CONNECTION_SLUG,
    COUNT(S.SYNC_ID)                    AS TOTAL_SYNCS,
    COUNT(CASE WHEN S.HEALTH_STATE = 'HEALTHY'    THEN 1 END) AS HEALTHY_SYNCS,
    COUNT(CASE WHEN S.HEALTH_STATE = 'FAILED'     THEN 1 END) AS FAILED_SYNCS,
    COUNT(CASE WHEN S.HEALTH_STATE = 'INCOMPLETE' THEN 1 END) AS INCOMPLETE_SYNCS,
    COUNT(CASE WHEN S.RUN_STATE    = 'PAUSED'     THEN 1 END) AS PAUSED_SYNCS
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON S.CONNECTION_ID = C.CONNECTION_ID
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY C.IS_PRODUCTION_ENVIRONMENT DESC, APP, C.CONNECTION_NAME
```

**Present as a table and flag:**
- **Orphaned connections** — `TOTAL_SYNCS = 0` (connection exists but has no syncs; may be stale or unused)
- **Production connections with failures** — `IS_PRODUCTION = TRUE` and `FAILED_SYNCS > 0`
- **Production connections with incomplete syncs** — `IS_PRODUCTION = TRUE` and `INCOMPLETE_SYNCS > 0`

#### Step 2: Syncs Per Connection (detail view)

**Goal:** Show the individual syncs for each connection with their current status.

**Execute:**

```sql
SELECT
    C.CONNECTION_NAME,
    SPLIT_PART(C.PLUGIN_FQN, '__', 2)   AS APP,
    C.IS_PRODUCTION_ENVIRONMENT         AS IS_PRODUCTION,
    S.SYNC_NAME,
    S.SYNC_DIRECTION,
    S.HEALTH_STATE,
    S.RUN_STATE,
    S.LATEST_RUN_START,
    S.SYNC_SCHEDULE:mode::VARCHAR        AS SCHEDULE_MODE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON S.CONNECTION_ID = C.CONNECTION_ID
ORDER BY C.IS_PRODUCTION_ENVIRONMENT DESC, APP, C.CONNECTION_NAME, S.SYNC_NAME
```

Present grouped by connection. For each connection show:
- Whether it is production or non-production
- The authentication method used
- Each sync's direction, health state, run state, and last run time

#### Step 3: Assess Connection Health (inferred)

**Goal:** Since no TEST_CONNECTION API exists, infer whether a connection is healthy by examining recent sync run outcomes for all syncs that use it. Auth failures, permission errors, and connectivity issues surface as `GLOBAL_ERROR` patterns on sync runs.

**Execute:**

```sql
SELECT
    C.CONNECTION_NAME,
    SPLIT_PART(C.PLUGIN_FQN, '__', 2)          AS APP,
    C.CONNECTION_METHOD,
    C.IS_PRODUCTION_ENVIRONMENT                AS IS_PRODUCTION,
    COUNT(DISTINCT S.SYNC_ID)                  AS TOTAL_SYNCS,
    COUNT(DISTINCT R.SYNC_RUN_ID)              AS RECENT_RUNS,
    COUNT(DISTINCT CASE WHEN R.HEALTH_STATE = 'HEALTHY' THEN R.SYNC_RUN_ID END) AS SUCCESSFUL_RUNS,
    COUNT(DISTINCT CASE WHEN R.HEALTH_STATE = 'FAILED'  THEN R.SYNC_RUN_ID END) AS FAILED_RUNS,
    MAX(CASE WHEN R.HEALTH_STATE = 'HEALTHY' THEN R.RUN_END_DATETIME END)       AS LAST_SUCCESS,
    MAX(CASE WHEN R.HEALTH_STATE = 'FAILED'  THEN R.RUN_END_DATETIME END)       AS LAST_FAILURE,
    LISTAGG(DISTINCT
        CASE WHEN R.HEALTH_STATE = 'FAILED' AND R.GLOBAL_ERROR IS NOT NULL
             THEN LEFT(R.GLOBAL_ERROR, 120)
        END, ' | '
    )                                          AS RECENT_ERROR_SAMPLES
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON S.CONNECTION_ID = C.CONNECTION_ID
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN R ON R.SYNC_ID = S.SYNC_ID
    AND R.RUN_START_DATETIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2, 3, 4
ORDER BY FAILED_RUNS DESC, C.IS_PRODUCTION_ENVIRONMENT DESC, C.CONNECTION_NAME
```

**Interpret the results using this triage table:**

| Pattern | Likely Cause | Recommendation |
|---|---|---|
| `FAILED_RUNS > 0` and `SUCCESSFUL_RUNS = 0` for all syncs on this connection | Connection-level issue (auth expired, endpoint down, permissions revoked) | Credentials or connectivity are broken at the connection level. The user must fix this in the **Omnata UI** — edit the connection and re-complete the wizard to re-authenticate and re-validate. This cannot be done from SQL. |
| `FAILED_RUNS > 0` but some syncs on this connection still succeed | Sync-level issue, not connection-level — the connection itself is working | Route to `references/sync-management.md` (Part 1) for per-sync diagnosis |
| `RECENT_RUNS = 0` and `TOTAL_SYNCS > 0` | All syncs paused or no schedule | Check `RUN_STATE` in Step 2 results |
| `RECENT_RUNS = 0` and `TOTAL_SYNCS = 0` | Orphaned connection — no syncs use it | Flag as potentially stale; suggest cleanup via Step 5 (`DELETE_CONNECTION`) if appropriate |
| `LAST_FAILURE > LAST_SUCCESS` | Most recent activity was a failure | Check `RECENT_ERROR_SAMPLES` for auth/connectivity patterns |
| `RECENT_ERROR_SAMPLES` contains `401`, `403`, `authentication`, `token`, `unauthorized`, `expired` | Authentication/authorization failure — OAuth token or API key has expired or been revoked | Credentials must be refreshed in the **Omnata UI** connection wizard (Account Admin required for the underlying Security Integration and Secrets). Cannot be fixed from SQL. |
| `RECENT_ERROR_SAMPLES` contains `timeout`, `connection refused`, `network`, `DNS` | Network/connectivity issue | Check Snowflake network rules and External Access Integration via Step 5 (`NETWORK_RULE_NAME`, `EXTERNAL_ACCESS_INTEGRATION_NAME`). If the EAI or Network Rule needs updating, this must be done through the **Omnata UI** or by an Account Admin — the Omnata wizard manages these objects. |

#### Step 4: Connection History (optional)

**Goal:** Show the full lifecycle of a connection — when it was created, when credentials were changed, and when it was tested — from the Snowflake event table. Use this when investigating consecutive sync failures with ambiguous errors to determine whether a credential change coincides with the failure window.

**When to use:**
- User asks when a connection was created or when credentials last changed
- A sync was failing with vague errors (HTTP 500, connection refused, retry exhaustion) but is now healthy and the cause is unclear — a credential rotation may explain it
- You want to confirm that a connection edit followed by sync recovery means the edit fixed the issue

**Prerequisites:** Requires access to the account event table. First discover the event table location by running `SHOW PARAMETERS LIKE 'EVENT_TABLE' IN ACCOUNT` — see Step 0 of `references/event-table-diagnostics.md` for full guidance including role requirements (`EVENTS_VIEWER` or `EVENTS_ADMIN`).

##### Step 4a: Connection lifecycle events

Connection creation, editing, and deletion all execute through `OMNATA_SYNC_ENGINE` API procedures. Query the event table using the app name discovered in `event-table-diagnostics.md` Step 1:

```sql
SELECT
    TIMESTAMP,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE,
    RECORD:name::VARCHAR                                    AS SPAN_NAME,
    RECORD_TYPE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR = '<omnata_app_name>'
  AND RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR ILIKE ANY (
      '%BEGIN_CONNECTION_CREATION%',
      '%COMPLETE_CONNECTION_CREATION%',
      '%BEGIN_CONNECTION_EDIT%',
      '%CANCEL_CONNECTION_CREATION%',
      '%DELETE_CONNECTION%',
      '%SET_CONNECTION_ENVIRONMENT%'
  )
ORDER BY TIMESTAMP
```

> **Note:** Connection lifecycle events do not include the connection slug or ID in their attributes. To associate events with a specific connection, correlate by timestamp proximity to known sync activity for that connection (from `SYNC_RUN.RUN_START_DATETIME`).

##### Step 4b: Secret and credential update events

OAuth tokens and API keys are written to Snowflake Secrets by the connector plugin app, not by `OMNATA_SYNC_ENGINE`. Plugin apps always contain `PLUGIN` in their name (e.g. `OMNATA_SALESFORCE_PLUGIN`, `OMNATA_HUBSPOT_PLUGIN`):

```sql
SELECT
    TIMESTAMP,
    RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR    AS APP_NAME,
    RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR     AS EXECUTABLE,
    RECORD:name::VARCHAR                                    AS SPAN_NAME,
    RECORD_TYPE
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"snow.application.name"::VARCHAR ILIKE '%PLUGIN%'
  AND RESOURCE_ATTRIBUTES:"snow.executable.name"::VARCHAR ILIKE ANY (
      '%UPDATE_GENERIC_SECRET%',
      '%CONFIGURE_APIS%',
      '%CONNECTION_TEST%',
      '%NETWORK_ADDRESSES%'
  )
  AND TIMESTAMP BETWEEN '<start>' AND '<end>'
ORDER BY TIMESTAMP
```

##### Step 4c: Interpreting the timeline

| Event | Meaning |
|---|---|
| `BEGIN_CONNECTION_CREATION` | A new connection was started |
| `COMPLETE_CONNECTION_CREATION` | Connection saved with parameters and secrets |
| `BEGIN_CONNECTION_EDIT` | An existing connection's credentials were being replaced |
| `UPDATE_GENERIC_SECRET_OBJECT` | OAuth or other secrets were written or updated |
| `CONNECTION_TEST` | The connection was tested (usually after creation or edit) |
| `CONFIGURE_APIS` | The plugin reconfigured its API endpoints for the connection |
| `CANCEL_CONNECTION_CREATION` | A connection creation was abandoned before completion |
| `DELETE_CONNECTION` | A connection was removed |
| `SET_CONNECTION_ENVIRONMENT` | The production/non-production flag was changed |

A typical **connection creation** sequence: `BEGIN_CONNECTION_CREATION` → `CONFIGURE_APIS` → `COMPLETE_CONNECTION_CREATION` → `UPDATE_GENERIC_SECRET_OBJECT` → `CONNECTION_TEST`

A typical **connection edit** sequence: `BEGIN_CONNECTION_EDIT` → `CONFIGURE_APIS` → `COMPLETE_CONNECTION_CREATION` → `UPDATE_GENERIC_SECRET_OBJECT` → `CONNECTION_TEST`

##### Correlating with sync failures

If investigating whether a credential change explains a run of sync failures, compare the connection edit timestamps against the failure window from `SYNC_RUN`. The pattern to look for:

- Consecutive sync failures with the same vague error (HTTP 500, timeout, connection refused)
- A `BEGIN_CONNECTION_EDIT` + `UPDATE_GENERIC_SECRET_OBJECT` occurring during or shortly after the failure window
- Syncs succeeding after the edit completes

This pattern indicates the failures were caused by invalid credentials — some platforms return HTTP 500 for expired credentials rather than a clean 401, making the root cause easy to miss without the connection history.

---

#### Step 5: Connection Lookup (optional)

If the user asks about a specific app or connection by name:

```sql
SELECT
    C.CONNECTION_ID,
    C.CONNECTION_NAME,
    C.PLUGIN_FQN,
    C.CONNECTION_METHOD,
    C.IS_PRODUCTION_ENVIRONMENT,
    C.CONNECTION_SLUG,
    C.EXTERNAL_ACCESS_INTEGRATION_NAME,
    C.NETWORK_RULE_NAME
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C
WHERE C.CONNECTION_NAME ILIKE '%<user_provided_name>%'
   OR SPLIT_PART(C.PLUGIN_FQN, '__', 2) ILIKE '%<user_provided_name>%'
ORDER BY C.IS_PRODUCTION_ENVIRONMENT DESC, C.CONNECTION_NAME
```

This surfaces the Snowflake infrastructure object names (`EXTERNAL_ACCESS_INTEGRATION_NAME`, `NETWORK_RULE_NAME`) which are useful when troubleshooting connectivity issues at the Snowflake level.


### Stopping Points

- After Step 1 for a high-level connection health summary
- After Step 2 when the user wants to see exactly which syncs belong to each connection
- After Step 3 when the user wants to assess whether a connection's credentials or connectivity are working (inferred from sync run data)
- After Step 4 when the user is investigating connection history or correlating credential changes with a sync failure window
- After Step 5 when the user is looking for a specific connection or app
- Before any connection action in Part 2, only when the user explicitly asks for it

## Part 2: Connection actions

> These procedures aren't in the public Omnata docs yet. They're supported and work on current
> versions; check the procedure list in the Sync Engine before relying on one. Only suggest them
> when the user explicitly needs to perform these operations. To create a connection, use `references/configure-connections.md`.
> To edit credentials or re-authenticate an existing connection, see "Edit an existing connection" in `references/configure-connections.md`.

### Delete a Connection

Permanently deletes a connection. **Irreversible.** It fails if any syncs still reference it. Show the user the connection's name and ID, and confirm before calling it.

**Before running:** this permanently deletes the connection. Show the user its name and ID, check that no syncs use it, and get their confirmation.

```sql
-- ⚠️ UNDOCUMENTED. Irreversible.
-- <connection_id> is CONNECTION_ID from DATA_VIEWS.CONNECTION
CALL OMNATA_SYNC_ENGINE.API.DELETE_CONNECTION(<connection_id>);
```

Before calling: confirm `TOTAL_SYNCS = 0` for this connection (see Part 1, Step 1
Step 1), or that all syncs have already been deleted or reassigned.

---

### Set Connection Environment

Changes whether a connection is production or non-production, without an edit session. See `references/branching.md` for what the flag controls.

**Before running:** changing the production flag changes which syncs and branches can use this connection. Explain the effect, and get the user's confirmation.

```sql
-- ⚠️ UNDOCUMENTED.
CALL OMNATA_SYNC_ENGINE.API.SET_CONNECTION_ENVIRONMENT(<connection_id>, <is_production_environment>);
```

---

### Reassign a Sync to a Different Connection

Moves a sync's main, or one branch, to another connection of the **same plugin**. Useful when consolidating connections or handing over credentials.

**Before running:** the sync's next runs use the new connection's credentials and account. Show the user both connections, and get their confirmation.

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

### Clean Up Syncs and Connections

Use this to remove test setups, or a connection and everything on it. Always list what will be deleted and get the user's confirmation before deleting anything.

1. **List the syncs on the connection:**
   ```sql
   SELECT S.SYNC_ID, S.SYNC_SLUG, S.SYNC_NAME, S.SYNC_DIRECTION
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
   JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C ON C.CONNECTION_ID = S.CONNECTION_ID
   WHERE C.CONNECTION_SLUG = '<connection_slug>';
   ```
2. **Show the user the syncs and the connection, and confirm.**

   > **Warning: irreversible.** Deleting each sync also permanently deletes its inbound raw tables and normalized views. Say so explicitly, and wait for the user's explicit yes.
3. **Delete each sync** with `DELETE_SYNC` (see "Delete a Sync" in `references/sync-management.md`).
4. **Delete the connection** with `DELETE_CONNECTION` ("Delete a Connection" above). It fails while any sync still references it.
5. **Confirm** the connection and syncs no longer appear in `DATA_VIEWS.CONNECTION` and `DATA_VIEWS.SYNC`.
6. **Local secrets.** If the connection was created with the secure secret path, offer `cortex secret delete <key>` for each stored secret.

**Everything for a plugin.** Only when the user asks to remove all of a plugin's syncs and connections, for example before uninstalling it:
1. List every sync and connection for the plugin (`DATA_VIEWS.SYNC` and `DATA_VIEWS.CONNECTION` filtered on `PLUGIN_FQN`), with the inbound tables that will go.
2. Show the full list and get the user's explicit confirmation.
3. Call `DELETE_ALL_SYNCS('<PLUGIN_FQN>')`, then `DELETE_ALL_CONNECTIONS('<PLUGIN_FQN>')`.
4. Confirm nothing for the plugin remains in either view.

To abandon a connection that was never completed, use `CANCEL_CONNECTION_CREATION` instead (see `references/configure-connections.md`).

---

## Quick reference

| Procedure | Parameters | Notes |
|---|---|---|
| `DELETE_CONNECTION` | `(CONNECTION_ID)` | ⚠️ Undocumented. Irreversible. |
| `BEGIN_CONNECTION_CREATION`, `BEGIN_CONNECTION_EDIT`, `UPDATE_CONNECTION_OBJECTS`, `COMPLETE_CONNECTION_CREATION`, `CANCEL_CONNECTION_CREATION` | see `references/configure-connections.md` | Create or edit a connection |
| `SET_CONNECTION_ENVIRONMENT` | `(CONNECTION_ID, IS_PRODUCTION_ENVIRONMENT)` | ⚠️ Undocumented. |
| `SET_SYNC_CONNECTION` | `(SYNC_ID, CONNECTION_ID, SYNC_BRANCH_ID)` | ⚠️ Undocumented. `SYNC_BRANCH_ID` NULL for main |
| `DELETE_ALL_SYNCS` / `DELETE_ALL_CONNECTIONS` | `(PLUGIN_FQN)` | **Deletes every sync (with its tables and views) or every connection for a plugin. Irreversible.** Use only through the "Clean Up Syncs and Connections" workflow above: list everything affected and get the user's explicit confirmation first |

Sync procedures are listed in `references/sync-management.md`.
