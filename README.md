# Omnata Sync Administration Skill

A Cortex Code skill for administering [Omnata Sync Engine](https://omnata.com) — a Snowflake Native Application. Load this skill into Cortex Code and ask questions in plain language; Cortex will query your `OMNATA_SYNC_ENGINE.DATA_VIEWS` schema and guide you through diagnosis and remediation.

The skill covers:

- **Sync health** — overall status dashboard, failed and incomplete syncs, re-run triage
- **Outbound syncs** — run history, failed records, error patterns, stuck and delayed records
- **Inbound syncs** — data freshness, stream failures, cursor state, stream audit trail
- **Connections** — health assessment, orphaned connections, re-authentication guidance, advanced connection management
- **Error diagnosis** — origin classification (Snowflake-side / endpoint-side / platform-level), remediation actions, error knowledge base
- **Event table diagnostics** — full stack traces, sync run lifecycle timelines, recurring error detection
- **Warehouse costs** — credit attribution per sync, dollar estimates, optimisation recommendations
- **Support handoff** — status page checks, support ticket assembly for Omnata

---

## File structure

When uploading files to this repository, use these exact paths (GitHub will create the subfolders automatically):

```
omnata-sync/SKILL.md
omnata-sync/README.md
omnata-sync/TEST-PROMPTS.md
omnata-sync/references/error-knowledge-base.md
omnata-sync/references/event-table-diagnostics.md
omnata-sync/references/monitoring-connections.md
omnata-sync/references/monitoring-inbound.md
omnata-sync/references/monitoring-outbound.md
omnata-sync/references/monitoring-sync-status.md
omnata-sync/references/monitoring-warehouse-cost.md
omnata-sync/references/support-handoff.md
```

---

## Installation

Choose the method that matches how you use Cortex Code:

- **[Option A — Snowsight Workspaces](#option-a--snowsight-workspaces)** (browser-based)
- **[Option B — Cortex CLI](#option-b--cortex-cli)** (terminal-based)

---

## Option A — Snowsight Workspaces

Skills in Snowsight live inside a workspace. The setup involves creating a Snowflake Git Repository object, then asking Cortex Code to copy the skill files into the workspace.

### Part 1: Account setup (one-time)

This part requires `ACCOUNTADMIN` for the API integration step. If you don't have that role, ask your Snowflake account administrator to run Step 1 for you, then continue from Step 2.

Paste this prompt into any Cortex Code session:

```
Please set up the Omnata Sync Administration skill in this Snowflake account.

Step 1 — Create the GitHub API integration (requires ACCOUNTADMIN).
Check whether an API integration for github.com/omnata-labs already exists. If not, create one:

    CREATE OR REPLACE API INTEGRATION omnata_github_integration
      API_PROVIDER = git_https_api
      API_ALLOWED_PREFIXES = ('https://github.com/omnata-labs')
      ENABLED = TRUE;

Step 2 — Create the Git repository object.
Ask me which database and schema to use, then create the repository:

    CREATE OR REPLACE GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill
      API_INTEGRATION = omnata_github_integration
      ORIGIN = 'https://github.com/omnata-labs/omnata-sync-administration-skill';

Step 3 — Fetch the latest files:

    ALTER GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill FETCH;

Step 4 — Verify the skill files are present:

    LIST @<my_database>.<my_schema>.omnata_sync_skill/branches/main/omnata-sync/;

Confirm the listing shows SKILL.md and a references/ folder.
```

### Part 2: Workspace setup

1. In Snowsight, go to **Projects → Workspaces** and create a new workspace called **Omnata Administration**
2. Open the workspace and start a Cortex Code session
3. Paste this prompt, substituting your database, schema, and repository name:

```
In database <my_database>, schema <my_schema>, there is a Git repository called
OMNATA_SYNC_SKILL containing a Cortex Code skill. Please install it as a permanent
skill in this workspace by copying the files into .snowflake/cortex/skills/omnata-sync/.
```

4. Verify the skill is loaded:

```
What skills do you have available?
```

### Updating (Snowsight)

When a new version is published, open your Omnata Administration workspace and paste:

```
Please fetch the latest files from the OMNATA_SYNC_SKILL git repository in
<my_database>.<my_schema> and update the omnata-sync skill in this workspace.
```

---

## Option B — Cortex CLI

The CLI method is simpler — just clone the repo directly into your local project's skills directory. No Snowflake Git Repository object required.

### Prerequisites

- Cortex CLI installed ([Snowflake docs](https://docs.snowflake.com/en/developer-guide/snowflake-cli/overview))
- Git installed locally

### Installation

```bash
# Navigate to your project directory
cd /path/to/your/project

# Create the skills directory if it doesn't exist
mkdir -p .snowflake/cortex/skills

# Clone the skill directly into the skills directory
git clone https://github.com/omnata-labs/omnata-sync-administration-skill \
  .snowflake/cortex/skills/omnata-sync
```

Start Cortex CLI — the skill is detected automatically. Verify with:

```
What skills do you have available?
```

### Updating (CLI)

```bash
cd .snowflake/cortex/skills/omnata-sync
git pull
```

---

## Using the skill

Once installed via either method, ask questions in plain language:

```
Check the health of all my Omnata syncs and give me a summary of what's failing or needs attention.
```

```
Which records are failing to sync in the CONTACTS to Airtable sync, and how do I fix them?
```

```
How much is Omnata costing me in Snowflake credits? Which syncs are the most expensive?
```
