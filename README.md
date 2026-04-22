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

## Installation

Copy the prompt below and paste it into Cortex Code in your Snowflake account. Cortex will run the setup steps for you.

> **Note:** Step 1 (API integration) requires `ACCOUNTADMIN`. If you don't have that role, ask your Snowflake account administrator to run Step 1 for you, then run Step 2 onwards yourself.

---

### Cortex setup prompt

```
Please set up the Omnata Sync Administration skill in this Snowflake account by running the following steps.

**Step 1 — Create the GitHub API integration (requires ACCOUNTADMIN)**

Check whether an API integration for github.com/omnata-labs already exists. If not, create one:

    CREATE OR REPLACE API INTEGRATION omnata_github_integration
      API_PROVIDER = git_https_api
      API_ALLOWED_PREFIXES = ('https://github.com/omnata-labs')
      ENABLED = TRUE;

**Step 2 — Create the Git repository object**

Ask me which database and schema I'd like to install the skill into, then create the Git repository there:

    CREATE OR REPLACE GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill
      API_INTEGRATION = omnata_github_integration
      ORIGIN = 'https://github.com/omnata-labs/omnata-sync-administration-skill';

**Step 3 — Fetch the latest files**

    ALTER GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill FETCH;

**Step 4 — Confirm**

Run the following and confirm the SKILL.md file is present:

    LIST @<my_database>.<my_schema>.omnata_sync_skill/branches/main/omnata-sync/;

Once the LIST shows the skill files, tell me the stage path to use when loading the skill in Cortex Code:

    @<my_database>.<my_schema>.omnata_sync_skill/branches/main/omnata-sync/SKILL.md
```

---

## Using the skill

Once installed, load the skill in Cortex Code by pointing to the stage path confirmed in Step 4 above. Then try a prompt like:

```
Check the health of all my Omnata syncs and give me a summary of what's failing or needs attention.
```

---

## Updating to the latest version

When a new version is published, pull the latest files with:

```sql
ALTER GIT REPOSITORY <my_database>.<my_schema>.omnata_sync_skill FETCH;
```

No other changes are needed — Cortex Code reads the files fresh each time the skill is invoked.
