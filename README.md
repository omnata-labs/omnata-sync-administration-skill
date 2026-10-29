# Omnata Sync Administration Skill

A Cortex Code skill for administering [Omnata Sync Engine](https://omnata.com) — a Snowflake Native Application. Ask CoCo about your Omnata syncs and connections; it queries your `OMNATA_SYNC_ENGINE.DATA_VIEWS` schema, guides you through diagnosis and remediation, and, once you confirm, makes changes through the Sync Engine's `API` procedures.

**The skill covers:**

- **Sync health** — overall status dashboard, failed and incomplete syncs, re-run triage, consecutive failure analysis
- **Outbound syncs** — run history, failed records, error patterns, stuck and delayed records
- **Inbound syncs** — data freshness, stream failures, cursor state, stream audit trail, normalized view repair
- **Connections** — create connections end to end with CoCo (API key, token, service account and OAuth), health assessment, lifecycle history, credential change detection, advanced connection management
- **Actions** — run, pause, resume, rename, reschedule and delete syncs, resync or skip outbound records, full refresh of inbound streams, move inbound tables, clean up test syncs, connections and orphaned objects, refresh schemas, recreate views, pre/post run hooks, full stored procedure interface
- **Sync configuration** — create and update inbound and outbound syncs programmatically via `CONFIGURE_OMNATA_INBOUND_SYNC` / `CONFIGURE_OMNATA_OUTBOUND_SYNC`, bulk stream setup, per-plugin reference pages
- **Branching and environments** — production vs non-production connections, test-first or straight-to-production guidance, dev/test branches, copying configuration between branches
- **Data management** — where inbound tables and views land: default storage location templates, per-sync locations, previews and collision checks before creating syncs
- **Error diagnosis** — origin classification (Snowflake-side / endpoint-side / platform-level), remediation actions, error knowledge base
- **Event table diagnostics** — full stack traces, sync run lifecycle timelines, recurring error detection
- **Warehouse costs** — credit attribution per sync, dollar estimates, schedule optimisation recommendations
- **Support handoff** — status page checks, support ticket assembly for Omnata

### What this skill can change

Besides reading data, the skill can make changes in your Snowflake account and in connected apps. Before any of these, CoCo lists what will be affected and asks you to confirm:
- **Deletes** syncs, branches or connections, permanently. Deleting a sync also deletes its inbound tables and views
- **Runs syncs and full refreshes**, which use warehouse credits and the source app's API rate limits
- **Configures outbound syncs that change data in other apps**: Replace, Delete or Mirror strategies, and actions such as Jira `DELETE_ISSUES`, overwrite or delete records in the destination. Outbound syncs also send Snowflake data to third-party services
- **Creates connections using credentials you supply** (API keys, tokens, service account keys, OAuth). CoCo recommends entering secrets in the Omnata UI, where they stay out of query history. It never asks you to paste a secret into the chat
- **Creates schemas and database roles**, transfers schema ownership and grants privileges for inbound storage locations
- **Runs a local Python script** that previews storage locations from a plan file
- **Fetches the public Snowflake and Omnata status pages** when preparing a support request

## Licence

Copyright 2026 Omnata. Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

---

## Installation

Choose the method that matches how you use Cortex Code:

- **[Option 1 — CoCo Desktop](#option-1--coco-desktop)** ✦ Recommended
- **[Option 2 — Cortex CLI](#option-2--cortex-cli)**
- **[Option 3 — Snowsight Workspaces](#option-3--snowsight-workspaces)**

---

## Option 1 — CoCo Desktop

The simplest installation method. CoCo Desktop fetches and manages the skill directly from GitHub — no Git clone or Snowflake objects required.

**Prerequisites:** [CoCo Desktop](https://www.snowflake.com/en/product/snowflake-coco/downloads/) installed and signed in to your Snowflake account.

### Install

1. Open the **Agent Settings** panel (left sidebar)
2. Select the **Skills** category
3. In the **GitHub Skills** section header, click **+** (Add from GitHub)
4. Enter the repository:
   ```
   omnata-labs/omnata-sync-administration-skill
   ```
5. Click **Add**

CoCo clones the repository, discovers all skill files, and registers the skill immediately. Verify by asking:

```
What skills do you have available?
```

> **Pinning to a release:** By default CoCo tracks the latest version on `main`, which is recommended for most users. To install a specific version you have reviewed, append its tag from the [Releases page](https://github.com/omnata-labs/omnata-sync-administration-skill/releases):
> `omnata-labs/omnata-sync-administration-skill#v<version>`

### Update

In the **Skills** tab of Agent Settings, find the skill under GitHub Skills and click **Update** — or click **Update all** to refresh all GitHub skills at once.

For more detail on managing skills in CoCo Desktop, see the [Snowflake documentation](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/skills).

---

## Option 2 — Cortex CLI

Clone the repository directly into your project's skills directory. No Snowflake objects required. Skills configuration is shared with CoCo Desktop via `~/.snowflake/cortex/skills.json`, so a skill added here is also available in the desktop app.

**Prerequisites:**
- [Cortex CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/overview) installed
- Git installed locally

### Install

```bash
# Navigate to your project directory
cd /path/to/your/project

# Create the skills directory if it doesn't exist
mkdir -p .snowflake/cortex/skills

# Clone the skill at a specific release tag (see the Releases page for the latest)
git clone --branch v<version> https://github.com/omnata-labs/omnata-sync-administration-skill \
  .snowflake/cortex/skills/omnata-sync
```

Start Cortex CLI — the skill is auto-detected. Verify with:

```
What skills do you have available?
```

### Update

```bash
cd .snowflake/cortex/skills/omnata-sync
git fetch --tags
git checkout v<new_version>
```

---

## Option 3 — Snowsight Workspaces

For browser-based Cortex Code in Snowsight. Skills live inside a workspace and are installed via a Snowflake Git Repository object.

### Part 1: Account setup (one-time)

This step requires `ACCOUNTADMIN` for the API integration. If you don't have that role, ask your Snowflake administrator to run Step 1, then continue from Step 2.

Paste this prompt into any Cortex Code session:

```
Please set up the Omnata Sync Administration skill in this Snowflake account.

Step 1 — Create the GitHub API integration (requires ACCOUNTADMIN).
Check whether an API integration called omnata_github_integration already exists by running SHOW API INTEGRATIONS. If it does not exist, create one:

    CREATE API INTEGRATION IF NOT EXISTS omnata_github_integration
      API_PROVIDER = git_https_api
      API_ALLOWED_PREFIXES = ('https://github.com/omnata-labs/omnata-sync-administration-skill')
      ENABLED = TRUE;

Step 2 — Create the Git repository object.
Ask me which database and schema to use, then create the repository:

    CREATE OR REPLACE GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill
      API_INTEGRATION = omnata_github_integration
      ORIGIN = 'https://github.com/omnata-labs/omnata-sync-administration-skill';

Step 3 — Fetch the latest files:

    ALTER GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill FETCH;

Step 4 — Verify the skill files are present:

    LIST @<my_database>.<my_schema>.omnata_sync_skill/tags/v<version>/;

Confirm the listing shows SKILL.md and a references/ folder.
```

### Part 2: Workspace setup

1. In Snowsight, go to **Projects → Workspaces** and create a new workspace called **Omnata Administration**
2. Open the workspace and start a Cortex Code session
3. Paste this prompt, substituting your database, schema, repository name and the release version from the [Releases page](https://github.com/omnata-labs/omnata-sync-administration-skill/releases):

```
In database <my_database>, schema <my_schema>, there is a Git repository called
OMNATA_SYNC_SKILL containing a Cortex Code skill. Please install version v<version> as a
permanent skill in this workspace by copying the files from the tags/v<version> path into
.snowflake/cortex/skills/omnata-sync/.
```

4. Verify the skill is loaded:

```
What skills do you have available?
```

### Update (Snowsight)

```sql
ALTER GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill FETCH;
```

Then in your Omnata Administration workspace:

```
Please update the omnata-sync skill from version v<current_version> to v<new_version> using the
OMNATA_SYNC_SKILL git repository in <my_database>.<my_schema>.
```

> **Staying on `main`:** If you prefer always-latest rather than pinned releases, use `branches/main` in place of `tags/<version>` in all paths above.

---

## Using the skill

Once installed, ask in plain language:

```
Check the health of all my Omnata syncs and give me a summary of what's failing.
```

```
Which inbound streams are failing in the Salesforce sync and why?
```

```
How much is Omnata costing me in Snowflake credits? Which syncs are most expensive?
```

```
Create a Slack notification sync that posts to #sales-alerts whenever a new row appears in MY_DB.EVENTS.NEW_SIGNUPS.
```

```
My normalized view for the Contact object is throwing a SQL error — what's wrong and how do I fix it?
```

---

## File structure

```
VERSION
SKILL.md
README.md
references/actions.md
references/branching.md
references/configure-connections.md
references/configure-syncs.md
references/data-management.md
references/error-knowledge-base.md
references/event-table-diagnostics.md
references/monitoring-connections.md
references/monitoring-inbound.md
references/monitoring-outbound.md
references/monitoring-sync-status.md
references/monitoring-warehouse-cost.md
references/support-handoff.md
references/plugins/  (README.md, _TEMPLATE.md and one page per plugin)
scripts/render_storage_location.py
.github/workflows/release.yml
```

---

## Releases

The current version is in `VERSION`. When a change merged to `main` bumps it, a GitHub Action tags the commit `v<version>` and publishes a release with generated notes. Patch bumps are for corrections and reference updates, minor bumps for new capabilities or plugin pages, and major bumps for breaking changes to how the skill is installed or used.
