# Omnata Sync Administration Skill

A Cortex Code skill for administering [Omnata Sync Engine](https://omnata.com) — a Snowflake Native Application. Load this skill and ask questions in plain language; CoCo queries your `OMNATA_SYNC_ENGINE.DATA_VIEWS` schema, guides you through diagnosis and remediation, and can take actions on your behalf.

**The skill covers:**

- **Sync health** — overall status dashboard, failed and incomplete syncs, re-run triage, consecutive failure analysis
- **Outbound syncs** — run history, failed records, error patterns, stuck and delayed records
- **Inbound syncs** — data freshness, stream failures, cursor state, stream audit trail, normalized view repair
- **Connections** — health assessment, lifecycle history, credential change detection, advanced connection management
- **Actions** — run, pause and resume syncs, refresh schemas, recreate views, pre/post hook reference, full stored procedure interface
- **Sync configuration** — create and update outbound syncs programmatically, bulk inbound stream setup via `CONFIGURE_OMNATA_OUTBOUND_SYNC` / `CONFIGURE_OMNATA_INBOUND_SYNC`
- **Error diagnosis** — origin classification (Snowflake-side / endpoint-side / platform-level), remediation actions, error knowledge base
- **Event table diagnostics** — full stack traces, sync run lifecycle timelines, recurring error detection
- **Warehouse costs** — credit attribution per sync, dollar estimates, schedule optimisation recommendations
- **Support handoff** — status page checks, support ticket assembly for Omnata

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

> **Pinning to a release:** To install a specific version instead of the latest, append the tag:
> `omnata-labs/omnata-sync-administration-skill#v1.0.0`

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

# Clone the skill at a specific release tag
git clone --branch v1.0.0 https://github.com/omnata-labs/omnata-sync-administration-skill \
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

    LIST @<my_database>.<my_schema>.omnata_sync_skill/tags/v1.0.0/omnata-sync/;

Confirm the listing shows SKILL.md and a references/ folder.
```

### Part 2: Workspace setup

1. In Snowsight, go to **Projects → Workspaces** and create a new workspace called **Omnata Administration**
2. Open the workspace and start a Cortex Code session
3. Paste this prompt, substituting your database, schema, and repository name:

```
In database <my_database>, schema <my_schema>, there is a Git repository called
OMNATA_SYNC_SKILL containing a Cortex Code skill. Please install version v1.0.0 as a
permanent skill in this workspace by copying the files from the tags/v1.0.0 path into
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
Please update the omnata-sync skill from version v1.0.0 to v<new_version> using the
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
omnata-sync/SKILL.md
omnata-sync/README.md
omnata-sync/TEST-PROMPTS.md
omnata-sync/references/actions.md
omnata-sync/references/configure-syncs.md
omnata-sync/references/error-knowledge-base.md
omnata-sync/references/event-table-diagnostics.md
omnata-sync/references/monitoring-connections.md
omnata-sync/references/monitoring-inbound.md
omnata-sync/references/monitoring-outbound.md
omnata-sync/references/monitoring-sync-status.md
omnata-sync/references/monitoring-warehouse-cost.md
omnata-sync/references/support-handoff.md
```
