<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-monitoring-connections
description: "Show the status of all Omnata connections and which syncs use them. Use when: user asks what connections are configured, wants to see which app connections exist, wants to find orphaned connections, wants to know which syncs use a particular connection, needs to understand which connections have failing syncs, wants to test a connection, asks about connection health, or needs to delete or reconfigure a connection. Triggers: omnata connections, connection status, what connections, connection health, orphaned connections, which syncs use, test connection, delete connection, connection environment, advanced connection."
---

# Omnata Connection Overview

List all configured connections, their associated syncs, and flag any issues.

## Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`

## Important: Connections MUST be created and configured through the Omnata UI

Omnata connections **cannot** be created, edited, re-authenticated, or tested via SQL stored procedures. The entire connection lifecycle — creation, credential configuration, testing, and editing — must go through the **Omnata web UI**.

**Why:** Each Omnata connection requires Snowflake infrastructure objects that need **ACCOUNTADMIN** privileges to create and manage:
- **External Access Integration** — controls which external endpoints the connection can reach
- **Security Integration** — manages OAuth flows for the destination app
- **Network Rule** — defines the allowed network endpoints
- **Secrets** — stores OAuth tokens and API credentials

The Omnata UI wizard orchestrates the creation of these objects, prompts the Account Admin to run the required `GRANT` statements, and then calls the plugin's `connect` method to validate connectivity. This multi-step flow cannot be replicated from SQL alone.

**If the user asks to create, edit, test, or re-authenticate a connection**, tell them:
> Omnata connections must be configured through the Omnata UI. This is because each connection requires External Access Integrations, Security Integrations, Network Rules, and Secrets — all of which need Account Admin privileges and a guided setup flow. To create a new connection, edit an existing one, or re-authenticate expired credentials, open the Omnata UI and use the connection wizard.

Then offer to **assess connection health indirectly** using Step 3 below, which infers connection status from recent sync run outcomes.

**Do NOT:**
- Call or suggest calling any `TEST_CONNECTION` procedure — it does not exist
- Suggest creating connections via `BEGIN_CONNECTION_CREATION` or `COMPLETE_CONNECTION_CREATION` — these are internal UI-only procedures
- Suggest manually creating External Access Integrations, Security Integrations, or Network Rules outside the Omnata UI — the Omnata wizard manages these objects and expects to own them
- Suggest any SQL-based workaround for connection creation or credential rotation

## Workflow

### Step 1: All Connections with Sync Summary

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

### Step 2: Syncs Per Connection (detail view)

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

### Step 3: Assess Connection Health (inferred)

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
| `FAILED_RUNS > 0` but some syncs on this connection still succeed | Sync-level issue, not connection-level — the connection itself is working | Route to `monitoring-sync-status.md` for per-sync diagnosis |
| `RECENT_RUNS = 0` and `TOTAL_SYNCS > 0` | All syncs paused or no schedule | Check `RUN_STATE` in Step 2 results |
| `RECENT_RUNS = 0` and `TOTAL_SYNCS = 0` | Orphaned connection — no syncs use it | Flag as potentially stale; suggest cleanup via Step 5 (`DELETE_CONNECTION`) if appropriate |
| `LAST_FAILURE > LAST_SUCCESS` | Most recent activity was a failure | Check `RECENT_ERROR_SAMPLES` for auth/connectivity patterns |
| `RECENT_ERROR_SAMPLES` contains `401`, `403`, `authentication`, `token`, `unauthorized`, `expired` | Authentication/authorization failure — OAuth token or API key has expired or been revoked | Credentials must be refreshed in the **Omnata UI** connection wizard (Account Admin required for the underlying Security Integration and Secrets). Cannot be fixed from SQL. |
| `RECENT_ERROR_SAMPLES` contains `timeout`, `connection refused`, `network`, `DNS` | Network/connectivity issue | Check Snowflake network rules and External Access Integration via Step 4 (`NETWORK_RULE_NAME`, `EXTERNAL_ACCESS_INTEGRATION_NAME`). If the EAI or Network Rule needs updating, this must be done through the **Omnata UI** or by an Account Admin — the Omnata wizard manages these objects. |

### Step 4: Connection Lookup (optional)

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

### Step 5: Advanced Connection Management (use with caution)

> **Warning:** The procedures in this step are **undocumented** in the official Omnata gitbook. They exist in the `API` schema and work, but Omnata has not published guidance on them. Only suggest these when the user explicitly needs to perform these operations, and always warn them that these are advanced, undocumented procedures that may change without notice.

> **Critical constraint:** These procedures can only **delete connections** or **change metadata flags** on existing connections. They **cannot** create connections, edit credentials, re-authenticate, or modify the underlying External Access Integrations, Security Integrations, Network Rules, or Secrets. All of those operations require **Account Admin** privileges and must go through the **Omnata UI connection wizard**. Do not present these procedures as alternatives to the UI for connection setup or credential management.

#### Delete a Connection

Permanently deletes a connection. **This will fail if any syncs still reference it** — delete or reassign syncs first.

```sql
-- ⚠️ UNDOCUMENTED — Advanced. Irreversible.
-- Arg: CONNECTION_ID (FLOAT) — get from Step 1 or Step 4 results
CALL OMNATA_SYNC_ENGINE.API.DELETE_CONNECTION(<connection_id>);
```

**Before calling**, confirm:
1. The connection has `TOTAL_SYNCS = 0` (from Step 1), or the user has already deleted/reassigned all syncs
2. The user understands this is permanent

#### Set Connection Environment Flags

Changes whether a connection is marked as production and/or has certain environment flags, without going through the full UI edit flow.

```sql
-- ⚠️ UNDOCUMENTED — Advanced.
-- Args: CONNECTION_ID (NUMBER), IS_PRODUCTION (BOOLEAN), IS_SANDBOX (BOOLEAN)
CALL OMNATA_SYNC_ENGINE.API.SET_CONNECTION_ENVIRONMENT(<connection_id>, <is_production>, <is_sandbox>);
```

Use cases:
- Promoting a staging connection to production after testing
- Demoting a production connection to non-production during maintenance

#### Other Undocumented Connection-Adjacent Procedures

These procedures are not documented but exist in the API schema. Mention them only if the user's question directly matches:

| Procedure | Signature | Purpose |
|---|---|---|
| `SET_SYNC_CONNECTION` | `(FLOAT, FLOAT, FLOAT)` → OBJECT | Reassign a sync (or branch) to a different connection. Useful when migrating syncs between connections. Args appear to be SYNC_ID, CONNECTION_ID, BRANCH_ID. |
| `SET_APP_SETTING` | `(VARCHAR, OBJECT)` → OBJECT | Set an application-level setting. The available setting names are not documented. |
| `SET_DEFAULT_INBOUND_STORAGE_LOCATION` | `(OBJECT)` → OBJECT | Set where inbound sync raw tables and views are created by default. |

> **Reminder:** These procedures are discovered from the installed application's API schema and are **not covered by Omnata's official documentation**. Behavior and signatures may change between Omnata versions. When in doubt, advise the user to contact Omnata support before using them.

## Stopping Points

- After Step 1 for a high-level connection health summary
- After Step 2 when the user wants to see exactly which syncs belong to each connection
- After Step 3 when the user wants to assess whether a connection's credentials or connectivity are working (inferred from sync run data)
- After Step 4 when the user is looking for a specific connection or app
- After Step 5 only when the user explicitly needs to delete, modify, or reconfigure connections via stored procedures
