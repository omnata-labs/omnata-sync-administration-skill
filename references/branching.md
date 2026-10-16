---
name: omnata-branching
description: "Explain and set up Omnata sync branching: production and non-production connections, testing sync changes on a branch before they reach production, and the single-environment testing patterns for outbound syncs. Use when: user asks about branching, test vs prod, dev and prod environments, sandbox connections, testing a sync before it goes live, or whether a connection should be production. Triggers: branching, branch, sync branch, test branch, dev and prod, sandbox, non-production connection, production connection, test before production, single environment, record filter branch, SYNC_BRANCH, single_account_branching."
---

# Branching

Branching is how Omnata manages change: you test sync changes on a branch before they reach production. This reference explains how it works and how CoCo sets it up. `references/configure-syncs.md` points here when a sync is being created, and `references/configure-connections.md` when production and non-production connections come up.

## How it works

- **Every sync has a `main` branch, and main is always production.** It's the sync that runs the day-to-day business.
- **A branch is a test copy of a sync**, usually named `test` or `dev`. It has its own connection, schedule, sync parameters, field mappings and source table. Branches are listed in `OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_BRANCH`.
- **Only a sync whose main connection is production can have branches.** Branching is turned on automatically for a sync on a production connection (and not multi-account). A sync on a non-production connection can't be branched.
- **Multi-account syncs don't use branching.** The same configuration is applied across several Snowflake accounts instead.

### Outbound matters most

- **Outbound syncs write to the target app**, so a change can break things there. Recommend branching for outbound syncs whenever the user has a way to test.
- **Inbound syncs only read**, so they can't break the source app. Branching is less important. An inbound branch writes to its own tables, so the storage location must include `{{branch_name}}` (the default table name does), or use Jinja such as `{% if branch_name=='main' %}PRODUCTION{% else %}TEST{% endif %}`.

## Connections and environments

When a connection is created, the user marks it production or non-production (`IS_PRODUCTION_ENVIRONMENT`). That choice decides what its syncs can do later:

| Connection | What its syncs can do |
|---|---|
| **Production** (the default) | Run as a sync's main branch, and be branched to a test environment |
| **Non-production** (a sandbox, test or dev instance of the app) | Be the connection for a branch. A sync created directly on it can't be branched. Treat that as a throwaway test sync: when it's right, set the sync up again against production |

What's available depends on the app. ERPs and Salesforce often have sandbox or test instances. Many other apps only have production.

The user has to think ahead a little: if they want to test on a sandbox and then promote the configuration to production, the sync should be created on the production connection with a branch on the sandbox connection, not created on the sandbox first. See "Workflow: production sync with a dev branch" below. If they only need test and production data kept apart, separate standalone syncs on each connection are simpler.

`OTHER_ENVIRONMENTS_EXIST` on the connection is obsolete. Ignore it.

## Testing patterns

| Pattern | When | Connections | Directions |
|---|---|---|---|
| **Separate environments** | The app has a sandbox or test instance | Main on the production connection, branch on a non-production connection to the same app | Outbound and inbound |
| **Same connection** | Testing changes without a second instance, e.g. a different set of inbound streams | Branch uses main's production connection | Outbound and inbound |
| **Single environment: alternate source via record filter** | Only production exists; test with a few records | Same production connection; the branch only handles the records listed in its branch record filter (`BRANCH_OUTBOUND_BRANCH_RECORD_FILTER`) | Outbound only |
| **Single environment: alternate source via table** | Only production exists; test from a different source table | Same production connection, different source table on the branch | Outbound only |
| **Single environment: alternate target** | Only production exists; send test data to a test area such as a folder, channel or dummy object | Same production connection, branch-only sync parameters point at the test area | Outbound only |

The single-environment mode (`SINGLE_ENVIRONMENT_BRANCHING_MODE`: `alternate_source_via_record_filter`, `alternate_source_via_table` or `alternate_target`) is set when the sync is created and can't be changed afterwards.

For outbound branches on a separate environment, the branch record state behaviour controls where the branch starts:
- `START_EMPTY` (default): sync every record from the beginning.
- `FORK_AND_IGNORE`: carry on from main, handle new records, ignore changes to existing ones.
- `FORK`: carry on from main. Use when the sandbox has a copy of production data.
- `SHARE`: same location as main, limited to the records in the branch record filter.

## Asking the user

Raise this when the user is **creating a sync**, not when creating a connection. The aim is to work out how strict the user is about change management and keeping test and production apart, then recommend the simplest setup that fits.

**1. Ask one question first:** "Are you trying this out on a test environment first, or going straight to your production environment?"

Skip the question if the request already answers it, e.g. "just sync our prod Salesforce" or "set this up on our sandbox first".

**2. Listen for how strict they are.** Signals:

| Leans towards **branching** (strict config promotion) | Leans towards **separate standalone syncs** (environment segregation for data) |
|---|---|
| "Changes must be tested before they reach production" | "We want test data kept separate from production data" |
| Approval or sign-off before production changes; change control, audit, UAT | Different teams or datasets per environment |
| "Promote", "deploy to prod", "release" | "We just want a dev copy to play with" |
| Outbound syncs where mistakes are costly (CRM, ERP, finance) | Inbound syncs, which only read |
| Wants the production sync's configuration to match exactly what was tested | Test and production can drift independently |

**3. Recommend, and explain briefly.** This is the core of the recommendation:

- **Strict config promotion: use branching.** The sync's main runs on production. A branch on the test environment is where changes are built and tested, then the tested configuration is promoted to main. Use the "Production sync with a dev branch" workflow below.
- **Environment segregation for data only: use separate standalone syncs.** One sync on the test connection and another on the production connection, each configured on its own. No branching needed. It's simpler, and fine when the user doesn't need the production configuration to come from a tested one.
- **Going straight to production:** create the sync on the production connection. For outbound syncs, mention once that branching is available later if they want to test changes. If the app has no test environment, the single-environment patterns can still test safely against production.
- **Trying it out on test with no plan for production yet:** a standalone sync on the test connection is fine. Tell the user that a sync created on a non-production connection can't be branched, so if they later want branching, the production sync is set up separately and the tested configuration recreated or copied there.

Start with a two- or three-sentence overview and the recommendation. Give more detail (patterns, record state options, the workflow steps) only as the user asks or chooses that path.

**Connection prerequisites.** Branching needs a production connection for main, and a non-production connection for a separate test environment. If one is missing, create it first with `references/configure-connections.md`, then come back here.

## Workflow: production sync with a dev branch

Use this when the user has two environments of the app, e.g. DEV and PROD, and wants to build and test the sync on DEV before it reaches PROD.

**Before starting**, check both connections exist for the same plugin, and their flags:

```sql
SELECT CONNECTION_ID, CONNECTION_SLUG, IS_PRODUCTION_ENVIRONMENT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION
WHERE PLUGIN_FQN = '<PLUGIN_FQN>';
```

The PROD connection must be production, and the DEV connection non-production. If one is missing, create it first (`configure-connections.md`).

**1. Create the main sync on PROD, with a minimal configuration.** Pass `CONNECTION_SLUG` keyed by branch, enable branching, and configure `main`. Keep main's configuration minimal so nothing meaningful runs against production yet. Use a manual schedule (`'mode': 'manual'`) so it doesn't run on its own.

```sql
-- Outbound example
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_OUTBOUND_SYNC(
    SYNC_SLUG => '<sync_slug>',
    SYNC_NAME => '<Sync name>',
    CONNECTION_SLUG => OBJECT_CONSTRUCT('main', '<prod_connection_slug>', '<branch_name>', '<dev_connection_slug>'),
    SYNC_PARAMETERS => <main_sync_parameters>,
    SYNC_SCHEDULE => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    SYNC_STRATEGY_NAME => '<strategy>',
    FIELD_MAPPINGS => <main_field_mappings>,
    SOURCE_TABLE => <source_table>,
    SINGLE_ACCOUNT_BRANCHING => true,
    SINGLE_ACCOUNT_BRANCH_TO_CONFIGURE => 'main',
    RAISE_ERRORS => true
);
```

Always create `main` first. If the first call targets a branch on a sync that doesn't exist yet, the sync is created on the branch's connection, which is wrong for this workflow.

**2. Create the branch on DEV with the real configuration.** Same call, same `CONNECTION_SLUG` object, with `SINGLE_ACCOUNT_BRANCH_TO_CONFIGURE => '<branch_name>'` and the configuration being built. Key `SYNC_SCHEDULE` by branch as well, e.g. `OBJECT_CONSTRUCT('main', <main schedule>, '<branch_name>', <branch schedule>)`; a plain schedule fails with `Sync schedule for Omnata branch name <branch_name> not found in provided object`. Each call targets one branch; the response shows `created_branch` or `updated_branch` and `updated_sync: false`, so main isn't touched. Choose `BRANCH_OUTBOUND_RECORD_STATE_BEHAVIOUR` (default `START_EMPTY`). The call returns `created_branch: true` and a `sync_branch_id`.

**3. Test on DEV.** Run the branch and check it, repeating step 2 with changes until it's right. If a run fails because of a column or key, the columns the plugin found for each stream are in `DATA_VIEWS.SYNC_BRANCH.INBOUND_LATEST_STREAMS_SCHEMA:"<stream>":properties`:

```sql
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(NULL, '<sync_slug>', '<branch_name>', 'external', OBJECT_CONSTRUCT(), true, true, current_user());
```

**4. Promote the tested configuration to main.** Copy the branch's configuration to main (see "Copying configuration between branches" below), then set main's real schedule and run main.

**5. Keep or remove the branch.** Keep it for testing future changes, or remove it with `CALL OMNATA_SYNC_ENGINE.API.DELETE_SYNC_BRANCH('<sync_slug>', '<branch_name>')`.

Inbound syncs follow the same order with `CONFIGURE_OMNATA_INBOUND_SYNC` (`SINGLE_ACCOUNT_BRANCHING`, `SINGLE_ACCOUNT_BRANCH_TO_CONFIGURE`, and `CONNECTION_SLUG` and `SYNC_SCHEDULE` keyed by branch). See `configure-syncs.md` for the inbound arguments.

Tested end to end on an inbound sync: branch created on a non-production connection, changed and run, then promoted to main with `SYNC_CONFIGURATION_ROLLBACK`, and main run healthy. The outbound variant follows the same steps but hasn't been run. If a step doesn't behave as described, stop, tell the user what happened, and offer to finish it in the Omnata UI.

## Copying configuration between branches

Configuration can be copied from any branch to any other branch of the same sync, including `main`. **Promoting** is the same copy, going from a lower environment to a higher one, e.g. from a `dev` branch to `main`. It's what "Copy config" does in the Omnata UI. Merging branches is no longer used.

1. **Find the source's current configuration version.** Main's is on `DATA_VIEWS.SYNC`, a branch's on `DATA_VIEWS.SYNC_BRANCH`:
   ```sql
   SELECT 'main' AS BRANCH_NAME, NULL AS SYNC_BRANCH_ID, SYNC_ID, CURRENT_SYNC_CONFIGURATION_VERSION_ID
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_SLUG = '<sync_slug>'
   UNION ALL
   SELECT B.BRANCH_NAME, B.SYNC_BRANCH_ID, B.SYNC_ID, B.CURRENT_SYNC_CONFIGURATION_VERSION_ID
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_BRANCH B
   JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON S.SYNC_ID = B.SYNC_ID
   WHERE S.SYNC_SLUG = '<sync_slug>';
   ```
2. **Show the user what will change and confirm.** For a promotion to main, this changes production behaviour.
3. **Copy it to the target:**
   ```sql
   CALL OMNATA_SYNC_ENGINE.API.SYNC_CONFIGURATION_ROLLBACK(
       <SYNC_ID>,
       <SOURCE_CONFIGURATION_VERSION_ID>,
       <TARGET_SYNC_BRANCH_ID>,  -- NULL to copy to main
       NULL                      -- CREATE_NEW_VERSION; the UI leaves this NULL
   );
   ```
   It returns `{"success": true, "data": {"target": [...], "sync_id": ..., "branch_id": ...}}`.
4. **Confirm** the target's `CURRENT_SYNC_CONFIGURATION_VERSION_ID` now matches the source's, then run the target. The result is `{"success": true, "data": {"target": ["sync"], ...}}` when the target is main.

What's copied: sync parameters, outbound field mappings and inbound streams configuration. What isn't copied, and stays as it is on the target: the connection, schedule, sync strategy, source table, tuning parameters, branch-only sync parameters and inbound storage location. If those need to change too, set them on the target with `CONFIGURE_OMNATA_*_SYNC` before or after copying.

The same procedure also rolls a sync or branch back to an earlier version of its own configuration: pass an older version ID from `DATA_VIEWS.SYNC_CONFIGURATION_VERSION`.

## Checking branches

```sql
SELECT S.SYNC_SLUG, B.BRANCH_NAME, C.CONNECTION_SLUG, C.IS_PRODUCTION_ENVIRONMENT,
       B.OUTBOUND_RECORD_STATE_BEHAVIOUR, B.OUTBOUND_BRANCH_RECORD_FILTER, B.HEALTH_STATE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_BRANCH B
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S ON S.SYNC_ID = B.SYNC_ID
LEFT JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C ON C.CONNECTION_ID = B.CONNECTION_ID;
```

`DATA_VIEWS.SYNC` has `BRANCHING_MODE_ENABLED` and `OUTBOUND_SINGLE_ENV_BRANCHING_MODE`. `DATA_VIEWS.SYNC_RUN.SYNC_BRANCH_ID` is null for main runs.
