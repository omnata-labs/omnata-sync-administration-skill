<!-- contributor: Cortex Code — Snowflake QUERY_HISTORY/TASK_HISTORY attribution, warehouse metering, cost estimation SQL -->
<!-- contributor: Co-work — Omnata task naming conventions, sync architecture, warehouse sizing guidance -->
---
name: omnata-monitoring-warehouse-cost
description: "Attribute Snowflake warehouse costs to Omnata syncs and UI usage. Use when: user asks about Omnata warehouse costs, credits used by syncs, which syncs cost the most, warehouse utilisation, cost attribution, or wants to optimise Omnata warehouse spend. Triggers: omnata cost, omnata credits, warehouse cost, sync cost, omnata warehouse, cost attribution, expensive syncs, warehouse utilisation, omnata spend."
---

# Omnata Warehouse Cost Attribution

Attribute Snowflake warehouse compute costs to individual Omnata syncs, the Omnata UI, and internal platform tasks.

## Prerequisites

- Active Snowflake connection with access to `OMNATA_SYNC_ENGINE.DATA_VIEWS`
- Access to `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` and `SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY`
- Access to `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`
- Note: ACCOUNT_USAGE views have up to 45 minutes of latency

## Background

### How Omnata Uses Warehouses

Omnata runs as a Snowflake Native App. All compute uses **customer-owned warehouses**, not serverless compute. The customer grants warehouse USAGE to the Omnata application, and all sync tasks, UI queries, and internal operations run on those warehouses.

Omnata recommends **XS warehouses** for API-based syncs. Database connectors may benefit from larger sizes. The guidance is to stack multiple syncs on a single XS warehouse until query queuing appears, then scale horizontally by adding another warehouse.

### Omnata Task Types

Omnata creates Snowflake tasks with these naming patterns:

| Task pattern | Purpose |
|---|---|
| `SYNC_RUNNER_<SYNC_ID>` | Orchestrator task for sync execution (main branch) |
| `SYNC_RUNNER_BG_<SYNC_ID>` | Background worker task for sync execution (main branch) |
| `SYNC_RUNNER_<SYNC_ID>_<BRANCH_ID>` | Orchestrator task for a sync branch |
| `SYNC_RUNNER_BG_<SYNC_ID>_<BRANCH_ID>` | Background worker task for a sync branch |
| `SYNC_SCHEDULER_<SYNC_ID>` | Legacy scheduler task (older sync configurations) |
| `SYNC_SCHEDULER_<SYNC_ID>_<BRANCH_ID>` | Legacy scheduler for a sync branch |
| `COLLABORATION_QUERY_RUNNER` | Internal collaboration/marketplace query task |
| `DAILY_BILLING` | Nightly Omnata licensing billing event — minimal cost |
| `OAUTH_FLOW_START` | One-time OAuth flow initiation — negligible cost |

The primary cost drivers are `SYNC_RUNNER_*` and `SYNC_RUNNER_BG_*` tasks. Each sync execution produces a pair: the orchestrator (SYNC_RUNNER) manages the run lifecycle, and the background worker (SYNC_RUNNER_BG) performs the actual data operations.

### Branching

Syncs can have branches (test, dev, QA) when `CONFIGURATION_MODE = 'advanced'` on the SYNC view. Branch tasks append `_<SYNC_BRANCH_ID>` to the task name. The SYNC_BRANCH view in DATA_VIEWS links `SYNC_BRANCH_ID` to `SYNC_ID` and `BRANCH_NAME`.

### Query Categories by QUERY_TAG

| QUERY_TAG pattern | Category | Description |
|---|---|---|
| `RUN_SYNC Sync` | Sync Execution | All sync-related queries (flat string, no sync ID) |
| JSON containing `StreamlitEngine` | Omnata UI | Streamlit app queries from the Omnata management UI |
| Stack trace / internal references | Native App Internal | Integration tests, internal maintenance |
| Empty or other | Untagged | Other queries on the granted warehouse |

Note: The `RUN_SYNC Sync` tag does not contain a sync ID. To attribute costs to individual syncs, use the TASK_HISTORY → QUERY_HISTORY join method below, not QUERY_TAG filtering.

## Workflow

### Step 1: Identify Omnata Warehouses

**Goal:** Find all warehouses granted to the Omnata application.

**Execute:**

```sql
SHOW GRANTS TO APPLICATION OMNATA_SYNC_ENGINE
```

Then filter for warehouse grants:

```sql
SELECT "name" AS WAREHOUSE_NAME, "privilege", "granted_by"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "granted_on" = 'WAREHOUSE'
ORDER BY "name"
```

Present the list of warehouses. If only one warehouse is granted, note this. If multiple warehouses are granted, subsequent queries will break down costs per warehouse.

### Step 2: Warehouse-Level Cost Overview

**Goal:** Show total warehouse credit consumption and estimate what proportion is attributable to Omnata.

**Execute:**

```sql
WITH omnata_warehouses AS (
    -- Replace with actual warehouse names from Step 1
    SELECT $1 AS WAREHOUSE_NAME FROM VALUES ('COMPUTE_WH')
),
warehouse_credits AS (
    SELECT
        wmh.WAREHOUSE_NAME,
        DATE_TRUNC('month', wmh.START_TIME) AS MONTH,
        ROUND(SUM(wmh.CREDITS_USED), 2) AS TOTAL_CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY wmh
    JOIN omnata_warehouses ow ON wmh.WAREHOUSE_NAME = ow.WAREHOUSE_NAME
    WHERE wmh.START_TIME >= DATEADD(month, -3, CURRENT_TIMESTAMP())
    GROUP BY 1, 2
),
omnata_query_credits AS (
    SELECT
        qh.WAREHOUSE_NAME,
        DATE_TRUNC('month', qh.START_TIME) AS MONTH,
        ROUND(SUM(qh.CREDITS_USED_CLOUD_SERVICES), 4) AS OMNATA_CLOUD_CREDITS,
        COUNT(*) AS OMNATA_QUERY_COUNT,
        ROUND(SUM(qh.TOTAL_ELAPSED_TIME) / 1000, 0) AS OMNATA_TOTAL_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh
    JOIN omnata_warehouses ow ON qh.WAREHOUSE_NAME = ow.WAREHOUSE_NAME
    WHERE qh.START_TIME >= DATEADD(month, -3, CURRENT_TIMESTAMP())
      AND (qh.QUERY_TAG = 'RUN_SYNC Sync'
           OR qh.QUERY_TAG ILIKE '%StreamlitEngine%'
           OR qh.QUERY_ID IN (
               SELECT th.QUERY_ID
               FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY th
               WHERE th.DATABASE_NAME ILIKE '%OMNATA%'
                 AND th.SCHEDULED_TIME >= DATEADD(month, -3, CURRENT_TIMESTAMP())
           ))
    GROUP BY 1, 2
)
SELECT
    wc.WAREHOUSE_NAME,
    wc.MONTH,
    wc.TOTAL_CREDITS AS WAREHOUSE_TOTAL_CREDITS,
    COALESCE(oqc.OMNATA_CLOUD_CREDITS, 0) AS OMNATA_CLOUD_CREDITS,
    COALESCE(oqc.OMNATA_QUERY_COUNT, 0) AS OMNATA_QUERIES,
    COALESCE(oqc.OMNATA_TOTAL_SECONDS, 0) AS OMNATA_ELAPSED_SECONDS
FROM warehouse_credits wc
LEFT JOIN omnata_query_credits oqc
    ON wc.WAREHOUSE_NAME = oqc.WAREHOUSE_NAME AND wc.MONTH = oqc.MONTH
ORDER BY wc.WAREHOUSE_NAME, wc.MONTH DESC
```

**Present and explain:**
- `WAREHOUSE_TOTAL_CREDITS` = total credits consumed by the warehouse (all workloads)
- `OMNATA_CLOUD_CREDITS` = cloud services credits directly from Omnata queries (this is typically small — most warehouse cost is in compute credits which are metered at the warehouse level, not per-query)
- `OMNATA_QUERIES` / `OMNATA_ELAPSED_SECONDS` = volume and time footprint of Omnata queries

**Important cost explanation:** Snowflake warehouse credits are consumed when the warehouse is running, regardless of which queries are executing. If Omnata is the **only** workload on a warehouse, then all warehouse credits are attributable to Omnata. If the warehouse is shared with other workloads, the best attribution is proportional: Omnata's share of total execution time on that warehouse approximates its share of warehouse credits.

### Step 2.5: Determine Credit Pricing

**Goal:** Detect the Snowflake account edition and warehouse generation to convert credits into estimated USD.

**Detect account edition:**

First, try to query the edition directly (requires ORGADMIN or organization-level access):

```sql
SELECT ACCOUNT_NAME, ACCOUNT_LOCATOR, EDITION, REGION
FROM SNOWFLAKE.ORGANIZATION_USAGE.ACCOUNTS
WHERE ACCOUNT_LOCATOR = CURRENT_ACCOUNT()
```

If this returns no rows (common — most accounts don't have org-level access), infer the edition from available features:
- If the account has **multi-cluster warehouses** (MAX_CLUSTER_COUNT > 1 in SHOW WAREHOUSES output), it is **Enterprise or higher**
- If not, it may be Standard edition

**Detect warehouse generation:**

Check if the warehouse is Gen1 or Gen2, since Gen2 has different credit rates:

```sql
SELECT "name", "size", "generation"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "name" IN (/* warehouse names from Step 1 */)
```

Note: Use the SHOW WAREHOUSES result from Step 1 if already available. The `generation` column will show `None` for Gen1 or `2` for Gen2.

**Check for contract-level pricing (if org access is available):**

```sql
SELECT *
FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY
WHERE USAGE_DATE = CURRENT_DATE()
  AND SERVICE_TYPE = 'COMPUTE'
LIMIT 10
```

If this returns data, use the `EFFECTIVE_RATE` as the $/credit. If it returns no rows, use list pricing.

**Credit-to-dollar conversion table:**

An XS warehouse consumes **1 credit/hour** per cluster (Gen1). Each size step doubles the rate. For multi-cluster warehouses, multiply by the number of active clusters.

| Warehouse Size | Credits/Hour (Gen1) | Credits/Hour (Gen2) |
|---|---|---|
| XS | 1 | 1.25 |
| S | 2 | 2.5 |
| M | 4 | 5 |
| L | 8 | 10 |
| XL | 16 | 20 |

Standard on-demand list pricing (USD per credit) by edition — actual rates depend on cloud provider, region, and whether the customer has a capacity contract:

| Edition | On-Demand $/credit (approx.) |
|---|---|
| Standard | ~$2.00 |
| Enterprise | ~$3.00 |
| Business Critical | ~$4.00 |

**Present:**
- State the detected (or inferred) edition and the list price used
- Note that capacity contracts typically offer 20–40% discounts — the estimates are upper bounds
- If RATE_SHEET_DAILY returned data, use the actual contract rate instead and note this

**Apply to all subsequent dollar estimates:**
- `estimated_cost_usd = credits × $/credit`
- For Omnata's share on a shared warehouse: `omnata_cost_usd = total_warehouse_credits × (omnata_elapsed_time / total_warehouse_elapsed_time) × $/credit`

### Step 3: Per-Sync Cost Attribution

**Goal:** Attribute warehouse time and query volume to each individual sync using the TASK_HISTORY → QUERY_HISTORY join.

**How it works:**
1. Each Omnata sync run creates task executions in `TASK_HISTORY`
2. The task's `QUERY_ID` joins to `QUERY_HISTORY` to find the `SESSION_ID`
3. All queries in that `SESSION_ID` within the task's time window belong to that sync run
4. Aggregate per sync to get total execution time and query count

**Execute:**

```sql
WITH task_sessions AS (
    SELECT
        th.NAME AS TASK_NAME,
        th.QUERY_ID AS TASK_QUERY_ID,
        th.SCHEDULED_TIME,
        th.COMPLETED_TIME,
        qh.SESSION_ID,
        -- Extract sync ID from task name
        CASE
            WHEN th.NAME LIKE 'SYNC_RUNNER_BG_%' THEN
                REGEXP_SUBSTR(th.NAME, 'SYNC_RUNNER_BG_(\\d+)', 1, 1, 'e')::INTEGER
            WHEN th.NAME LIKE 'SYNC_RUNNER_%' THEN
                REGEXP_SUBSTR(th.NAME, 'SYNC_RUNNER_(\\d+)', 1, 1, 'e')::INTEGER
            WHEN th.NAME LIKE 'SYNC_SCHEDULER_%' THEN
                REGEXP_SUBSTR(th.NAME, 'SYNC_SCHEDULER_(\\d+)', 1, 1, 'e')::INTEGER
        END AS SYNC_ID,
        CASE
            WHEN th.NAME LIKE 'SYNC_RUNNER_BG_%' THEN 'BACKGROUND'
            WHEN th.NAME LIKE 'SYNC_SCHEDULER_%' THEN 'SCHEDULER'
            ELSE 'ORCHESTRATOR'
        END AS TASK_ROLE
    FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY th
    JOIN SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh ON th.QUERY_ID = qh.QUERY_ID
    WHERE th.DATABASE_NAME ILIKE '%OMNATA%'
      AND th.NAME LIKE 'SYNC_%'
      AND th.SCHEDULED_TIME >= DATEADD(month, -1, CURRENT_TIMESTAMP())
),
sync_queries AS (
    SELECT
        ts.SYNC_ID,
        ts.TASK_ROLE,
        qh.QUERY_ID,
        qh.TOTAL_ELAPSED_TIME,
        qh.CREDITS_USED_CLOUD_SERVICES,
        qh.WAREHOUSE_NAME,
        qh.WAREHOUSE_SIZE
    FROM task_sessions ts
    JOIN SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh
        ON qh.SESSION_ID = ts.SESSION_ID
        AND qh.START_TIME BETWEEN ts.SCHEDULED_TIME AND COALESCE(ts.COMPLETED_TIME, CURRENT_TIMESTAMP())
    WHERE ts.SYNC_ID IS NOT NULL
)
SELECT
    sq.SYNC_ID,
    s.SYNC_NAME,
    SPLIT_PART(s.PLUGIN_FQN, '__', 2) AS APP,
    s.SYNC_DIRECTION,
    sq.WAREHOUSE_NAME,
    COUNT(sq.QUERY_ID) AS TOTAL_QUERIES,
    ROUND(SUM(sq.TOTAL_ELAPSED_TIME) / 1000, 1) AS TOTAL_ELAPSED_SECS,
    ROUND(SUM(sq.CREDITS_USED_CLOUD_SERVICES), 6) AS CLOUD_CREDITS,
    ROUND(SUM(sq.TOTAL_ELAPSED_TIME) / 1000 / 3600, 4) AS ELAPSED_HOURS
FROM sync_queries sq
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC s ON sq.SYNC_ID = s.SYNC_ID
GROUP BY 1, 2, 3, 4, 5
ORDER BY TOTAL_ELAPSED_SECS DESC
```

**Present as a ranked table showing the most expensive syncs first.** For each sync:
- Total queries executed in the period
- Total elapsed time (seconds and hours) — this is the best proxy for warehouse cost share
- Cloud services credits (small but precise)
- **Estimated USD cost** — using the $/credit rate from Step 2.5

**Calculating per-sync dollar estimates:**
- Compute the sync's share of total Omnata elapsed time: `sync_pct = sync_elapsed_hours / total_omnata_elapsed_hours`
- Multiply by Omnata's estimated credit share: `sync_credits = omnata_estimated_credits × sync_pct`
- Convert to dollars: `sync_cost_usd = sync_credits × $/credit`
- Present both the estimated credits and USD for each sync

**Interpreting the results:**
- If the warehouse runs exclusively for Omnata, all warehouse credits are Omnata's — divide proportionally by sync elapsed time
- If shared, first estimate Omnata's total share (from Step 2), then subdivide among syncs
- Flag any sync consuming disproportionate elapsed time relative to others
- Syncs showing `None` for SYNC_NAME/APP/DIRECTION are **deleted syncs** whose task history remains in ACCOUNT_USAGE — note this and suggest checking for orphaned tasks that may still be scheduled

### Step 4: Cost by Query Category

**Goal:** Break down warehouse usage into Omnata query categories — sync execution, UI, internal tasks.

**Execute:**

```sql
SELECT
    CASE
        WHEN qh.QUERY_TAG = 'RUN_SYNC Sync' THEN 'Sync Execution'
        WHEN qh.QUERY_TAG ILIKE '%StreamlitEngine%' THEN 'Omnata UI (Streamlit)'
        WHEN qh.QUERY_ID IN (
            SELECT th.QUERY_ID FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY th
            WHERE th.DATABASE_NAME ILIKE '%OMNATA%'
              AND th.NAME = 'DAILY_BILLING'
              AND th.SCHEDULED_TIME >= DATEADD(month, -1, CURRENT_TIMESTAMP())
        ) THEN 'Daily Billing'
        WHEN qh.QUERY_ID IN (
            SELECT th.QUERY_ID FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY th
            WHERE th.DATABASE_NAME ILIKE '%OMNATA%'
              AND th.NAME = 'COLLABORATION_QUERY_RUNNER'
              AND th.SCHEDULED_TIME >= DATEADD(month, -1, CURRENT_TIMESTAMP())
        ) THEN 'Collaboration Query Runner'
        ELSE 'Other/Untagged'
    END AS CATEGORY,
    COUNT(*) AS QUERY_COUNT,
    ROUND(SUM(qh.TOTAL_ELAPSED_TIME) / 1000, 0) AS ELAPSED_SECS,
    ROUND(SUM(qh.CREDITS_USED_CLOUD_SERVICES), 4) AS CLOUD_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh
WHERE qh.START_TIME >= DATEADD(month, -1, CURRENT_TIMESTAMP())
  AND (qh.QUERY_TAG = 'RUN_SYNC Sync'
       OR qh.QUERY_TAG ILIKE '%StreamlitEngine%'
       OR qh.QUERY_ID IN (
           SELECT th.QUERY_ID FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY th
           WHERE th.DATABASE_NAME ILIKE '%OMNATA%'
             AND th.SCHEDULED_TIME >= DATEADD(month, -1, CURRENT_TIMESTAMP())
       ))
GROUP BY 1
ORDER BY ELAPSED_SECS DESC
```

**Present and note:**
- **Sync Execution** is typically the dominant category
- **Omnata UI** cost is typically small and concentrated during initial setup/configuration periods. Once syncs are configured, UI usage drops significantly.
- **Daily Billing** is a nightly Omnata licensing task — should be minimal
- **Collaboration Query Runner** is internal marketplace/collaboration functionality
- Include **estimated USD** for each category using the same proportional method: `category_cost_usd = omnata_estimated_credits × (category_elapsed / total_omnata_elapsed) × $/credit`

### Step 5: Summary and Optimisation Recommendations

**Present a cost summary table** before recommendations:

| Metric | Credits | Est. USD |
|---|---|---|
| Total warehouse cost (all workloads) | X | $Y |
| Omnata estimated share | X | $Y |
| Top sync (name) | X | $Y |

Include the edition, $/credit rate used, and a caveat that capacity contracts will have lower rates.

**Then provide recommendations based on what you find:**

**If a warehouse is underutilised (Omnata is the only workload and total credits are low):**
- Consider sharing the warehouse with other light workloads, or reducing auto-suspend time
- Omnata recommends XS as the starting warehouse size for API syncs — confirm the warehouse is XS
- If the warehouse is larger than XS and only running API syncs, recommend downsizing — quantify the savings in USD (e.g. "Downsizing from S to XS would halve the credit rate from 2/hr to 1/hr, saving ~$X/month at current usage levels")

**If query queuing is detected:**
- Check `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` for queries with `QUEUED_OVERLOAD_TIME > 0` on Omnata warehouses
- This indicates the warehouse is saturated — consider splitting syncs across a second XS warehouse rather than scaling up

**If a single sync dominates cost:**
- Check whether it's an API sync or a database connector sync
- API syncs should be lightweight — a high-cost API sync may indicate excessive record volumes or a misconfigured schedule
- Database connector syncs may legitimately need more compute
- Quantify the cost: "Sync X accounts for Y% of Omnata cost, estimated at ~$Z/month"

**If UI costs are unexpectedly high:**
- This typically indicates active configuration/exploration — not a long-term concern
- If UI costs persist, check whether automated tools or scripts are hitting the Streamlit interface

**If the warehouse is shared with non-Omnata workloads:**
- Present Omnata's elapsed time as a proportion of total warehouse uptime
- Suggest tagging or separating workloads if the user needs precise cost attribution

**Cloud services 10% adjustment note:**
- Snowflake only bills cloud services credits that exceed 10% of daily compute credits
- If the account's daily cloud services are under 10% of compute, some or all cloud services credits shown may not actually be billed
- Mention this when presenting cloud services costs to avoid overstating actual charges

## Stopping Points

- After Step 1 if the user just wants to know which warehouses Omnata uses
- After Step 2 for a high-level credit overview (no dollar estimates yet)
- After Step 2.5 to add dollar estimates to the Step 2 credit numbers
- After Step 3 for per-sync cost ranking with dollar estimates
- After Step 4 for a category breakdown with dollar estimates
- After Step 5 for the full summary with optimisation guidance and dollar-denominated recommendations
