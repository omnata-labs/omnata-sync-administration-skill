---
name: omnata-data-management
description: "Design where inbound sync raw tables and normalized views land in Snowflake. Covers the three ways to operate storage locations: the app default, a custom default template (Settings > Data Management, SET_DEFAULT_INBOUND_STORAGE_LOCATION), and per-sync overrides (INBOUND_STORAGE_LOCATION). Use when: user wants to choose a database, schema or table naming for inbound data, set a storage location, build a naming system, change the default storage location, or check a template for collisions. Triggers: Omnata data management, Omnata storage location, inbound storage location, INBOUND_STORAGE_LOCATION, Omnata default storage location, SET_DEFAULT_INBOUND_STORAGE_LOCATION, where does my Omnata data land, which database do Omnata syncs write to, Omnata table naming, Omnata normalized view names, Omnata raw tables location."
---

# Data Management

Standalone reference for where and how Omnata stores inbound data in Snowflake. Other references (configure-syncs, actions, monitoring) link here rather than repeating it. It covers the inbound storage location: the app default, the custom default template (Settings > Data Management in the UI), per-sync overrides, and creating the location with the right privileges.

## Inbound storage location

An inbound sync writes each stream to a **raw table** and exposes it through a **normalized view**. Where both land is controlled by a storage location object. The template is very flexible: Jinja variables, filters, `{% if %}` blocks and string operators are all allowed. This guide narrows that down to a handful of patterns that are safe and easy to maintain.

### Step 1: Intent

There are three overall ways to operate storage locations across the app:

| Intent | What the user is choosing | Where it goes |
|---|---|---|
| **1. Use the default location** | Accepts the limits and rigidity of the app default: everything in the Omnata app database under `INBOUND_RAW` and `INBOUND_NORMALIZED` | Nothing to design. Omit `INBOUND_STORAGE_LOCATION` |
| **2. Custom default** | One templated naming system that works across all syncs with no overrides | **Fork A** |
| **3. Override per sync** | Leans on CoCo, or hard-codes values, to set each sync's location instead of building one overall template | **Fork B** |

How to pick the intent depends on how the user got here:
- **They asked about storage locations in general** (for example "where does my data land" or "change the default location"): ask with `ask_user_question`, offering all three intents.
- **They're configuring a sync**, through the procedure or with CoCo: the choice is made for this sync as part of the configuration. First check whether a custom default template is set (query in "How the default and overrides interact"). Then ask with `ask_user_question`:
  - **App default:** omit `INBOUND_STORAGE_LOCATION`
  - **Custom default** (only offer this if a template is set, and show it): preview it for this sync against existing syncs, then pass it explicitly as `INBOUND_STORAGE_LOCATION`, since the procedure doesn't apply it on its own
  - **Custom for this sync:** go to Fork B

  If no custom default is set, offer the app default and custom for this sync, and mention that a template for all syncs can be built with Fork A. Building one mid-configuration isn't required; it's the user's choice.

### Shared reference

Both forks use these sections.

#### Location keys

| Key | Default |
|---|---|
| `raw_database` | blank, meaning the Omnata app database |
| `raw_schema` | `INBOUND_RAW` |
| `raw_object` | `{{sync_slug}}_{{branch_name}}_{{stream_name}}` |
| `raw_table_type` | `standard` |
| `raw_table_standard_change_tracking` | `false`. Set `true` to enable change tracking on raw tables, for example to build dynamic tables or streams on them. Not available in the app database |
| `normalized_database` | blank, meaning the Omnata app database |
| `normalized_schema` | `INBOUND_NORMALIZED` |
| `normalized_object` | `{{sync_slug}}_{{branch_name}}_{{stream_name}}` |
| `normalized_column` | `{{column_name}}` |

Variables available in every key except `normalized_column`: `stream_name`, `sync_slug`, `branch_name` (`main` unless the sync is running in a branch), `plugin_id` and `sync_parameters.<key>` (plugin-specific, for example SQL Server has `database`, `schema` and `sync_type`). `normalized_column` only has `column_name`. These are Omnata template variables, not Snowflake variables, so never substitute them.

#### Writing the Jinja

Every key is a Jinja template, so CoCo can write logic to fit almost any description the user gives: conditions, string operations, length limits and so on. Use these sources when proposing logic:
- **Jinja Template Designer Documentation** (https://jinja.palletsprojects.com/en/stable/templates/): the standard syntax, the "List of Builtin Filters" and the "List of Builtin Tests". Any standard Jinja2 filter works
- **Omnata docs, Inbound > Customizing naming syntax**: the variables, and the Omnata custom filters `fivetran_word_division`, `multiple_underscores_to_single` and `prepend_starting_number_with_underscore`. The sync engine also provides `transliterate`, which turns accented characters into plain ASCII

Constructs that come up most:

| Need | Jinja |
|---|---|
| Change case | `{{ stream_name | upper }}`, `| lower`, `| title` |
| Replace or strip characters | `{{ stream_name | replace(".xlsx", "") | replace(" ", "_") }}`, `| trim` |
| Join values | `{{ plugin_id | upper }}_{{ stream_name | upper }}`, or `~` inside an expression |
| Branch on a value | `{%- if plugin_id == "mssql" -%}...{%- elif ... -%}...{%- else -%}...{%- endif -%}` |
| Match one of several values | `{% if stream_name in ["Account", "Contact"] %}` |
| Fall back when a value is missing | `{{ sync_parameters.database | default("NONE") }}` |
| Keep names short | `{{ stream_name[:50] }}` or `| truncate(50, true, "")` |
| Reuse a computed value | `{% set base = stream_name | lower | replace(" ", "_") %}{{ base | upper }}` |

Rules for templates:
- Don't include double quotes. The sync engine adds them as needed (Omnata docs)
- Use `{%-` and `-%}` around tags so no whitespace leaks into a name
- `sync_parameters.<key>` renders blank when the key doesn't exist for a plugin. Guard it with `default` or an `if`
- Always render a proposal with the preview script before showing it as final. It uses the same filters as the sync engine, so it catches syntax errors and unexpected names

#### Hard rules

These hold whatever the user chooses. Check every proposal against them.

| Rule | Consequence |
|---|---|
| **Every stream must render to a unique raw table** | The sync engine reuses any existing raw table with the same name, whichever sync created it, so two syncs writing to one raw table corrupts both, silently. Check for collisions with the preview script. Unlike normalized view clashes, this can't be accepted as a risk |
| **Custom schemas are rejected in the Omnata app database** | If `raw_database` or `normalized_database` is blank (the app database), the schema must be `INBOUND_RAW` or `INBOUND_NORMALIZED` |
| **Missing databases and schemas are only created if the app has the privilege** | Under the recommended setup (managed access schemas owned by a database role) the app has no `CREATE SCHEMA`, so every schema a template renders must be created first. A missing one fails with "insufficient privileges". See "Creating the location and privileges" |
| **Names are double-quoted, so case is kept exactly** | Add `| upper` if the user wants normal unquoted SQL (`select * from orders`) to work |
| **One template per sync, rendered per stream** | Anything that varies between syncs must come from a variable or an `{% if %}`, or be hard-coded in that sync's own template |
| **Hybrid raw tables must be in the app database** | Keep `raw_table_type` as `standard` when using a custom database |

#### How the default and overrides interact

How it works:
- The **custom default** is stored in `APP_SETTINGS` as `inbound_storage_location_defaults`. The UI's Create Sync flow copies it into each new sync at creation time. An existing sync only picks it up if it has no stored location at all. **Changing the default does not move existing syncs.**
- `CONFIGURE_OMNATA_INBOUND_SYNC` does **not** read the custom default. If `INBOUND_STORAGE_LOCATION` is omitted, the sync gets the built-in defaults above. To use the custom default from the procedure, read it and pass it explicitly:
  ```sql
  SELECT SETTING_VALUE FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.APP_SETTINGS
  WHERE SETTING_NAME = 'inbound_storage_location_defaults';
  ```
- A per-sync override is stored on the sync as `INBOUND_STORAGE_CONFIGURATION` and always wins over the default.

#### Capturing the design

Both custom paths start here. Users think in concrete table names rather than Jinja, so let them say what they want in their own words first, then fill the gaps.

##### 1. Open prompt
Before asking, pick one of the user's real streams (from the sync being configured, or an existing sync) and show where it would land today. Then ask in free text (not `ask_user_question`), for example:

> Where should your data land? Any of these works:
> - **Describe it**, for example "one schema per source database, table names uppercase"
> - **Give an example path**, for example "`AdventureWorks.dbo.Orders` should land at `ANALYTICS.ADVENTUREWORKS.ORDERS`"
> - **Paste a template** or an existing `INBOUND_STORAGE_LOCATION`
> - **Point to a database** in this Snowflake account that already has the structure you want
> - Or say **"guide me"** and I'll ask questions instead

In Fork B, if the existing syncs already follow a recognisable convention, summarise it and add **"follow the existing convention"** as the first suggestion.

##### 2. Work out the template
How to read each kind of answer:
- **Description:** map it to the layout checklist below and write the Jinja, using the patterns and "Writing the Jinja" as references. If the description needs logic the patterns don't cover (for example "Salesforce objects go in CRM, everything else in its own schema"), offer two options with `ask_user_question`, listing the simpler one first as the recommendation. Simpler is often better: a storage location is set once and lives for years, and plain templates are easier to read, preview and change later.
  - **Simplify the requirement (recommended):** CoCo suggests the nearest pattern that needs no logic (for example "one schema per plugin, so Salesforce lands in `SALESFORCE`"). Easier to maintain, but not exactly what was asked for
  - **Jinja logic:** CoCo writes conditions or filters that do exactly what was described, and shows the template and a preview. More precise, but the template is harder to read and every new exception means editing it
- **Example path:** match each part of the target path to a variable. For example `ADVENTUREWORKS` came from `sync_parameters.database` with `| upper`, and `ORDERS` came from `stream_name` with `| upper`. Anything that matches no variable is a fixed value
- **Pasted template:** check it only uses the keys listed above and valid variables and filters
- **Existing database:** see "Learning from an existing database" below
- **"Guide me":** go through the guided questions below

##### Learning from an existing database

1. **Confirm the scope.** "Replicate this database" could mean all of it or one part. If the user didn't say, list the schemas and ask which ones to follow.
2. **Check whether a current sync already writes there.** If one does, its `INBOUND_STORAGE_CONFIGURATION` is the exact template, so use it instead of inferring one:
   ```sql
   SELECT SYNC_SLUG, PLUGIN_FQN, INBOUND_STORAGE_CONFIGURATION
   FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
   WHERE INBOUND_STORAGE_CONFIGURATION::STRING ILIKE '%<database>%';
   ```
3. **Separate Omnata objects from user objects.** Learn the layout only from objects Omnata created. Raw tables have the columns `APP_IDENTIFIER`, `RECORD_DATA`, `RETRIEVE_DATE`, `IS_DELETED` and `RUN_ID`. Normalized views start with `OMNATA_APP_IDENTIFIER`, `OMNATA_RAW_RECORD` and other `OMNATA_*` columns:
   ```sql
   SELECT TABLE_SCHEMA, TABLE_NAME,
          LISTAGG(COLUMN_NAME, ',') WITHIN GROUP (ORDER BY ORDINAL_POSITION) AS OMNATA_COLUMNS
   FROM <database>.INFORMATION_SCHEMA.COLUMNS
   WHERE COLUMN_NAME IN ('APP_IDENTIFIER', 'RECORD_DATA', 'OMNATA_APP_IDENTIFIER', 'OMNATA_RAW_RECORD')
   GROUP BY 1, 2;
   ```
   Leave out other tables and views (demo tables, user-built views) and say that you've done so.
4. **Group by convention.** Group the Omnata objects by layout: how schemas are named, whether raw and normalized share a schema, and table prefixes or suffixes such as `_RAW` and `_NORMALIZED`. If there's more than one convention, show each with an example path and ask which to follow. Don't mix them.
5. **Recognise branches.** Schema or table names ending in `_MAIN`, `_TEST` or another branch name usually come from `{{branch_name}}`. Map them to the variable and treat it as a sign the source syncs had branching on. A suffix that only appears on some objects (for example `_TEST` on some, nothing on others) suggests the "main keeps clean names" condition in "Branches"
6. **Note the column casing** by sampling one normalized view's columns.
7. **Make raw names unique by default.** A copied layout may have been safe only for the single sync that made it. Keep the normalized layout the user sees, but add `{{ sync_slug | replace("-", "_") | upper }}` to `raw_object` unless the layout already makes raw names unique (also `{{ branch_name | upper }}` if branching is on). Tell the user you've done this and why.
8. **Ask whether to land in that database or copy its structure** somewhere else. If they choose to land there, list its existing tables and views and pass them to the preview as `existing_tables`, so paths that would reuse leftover objects are flagged.

##### 3. Fill the gaps
Check the result against the layout checklist (the guided questions below). Ask only about the points the user's answer didn't settle. The usual gaps:
- **Which database, exactly.** "Omnata" could mean a new `OMNATA` database or the app database `OMNATA_SYNC_ENGINE`. The app database only allows `INBOUND_RAW` and `INBOUND_NORMALIZED`, so any custom schema split needs a separate database
- **Where the raw tables go.** Users rarely mention them. Suggest a separate raw schema, and keep `{{sync_slug}}` in `raw_object`
- **Table name case.** Users often say "uppercase" for columns but not tables. Without `| upper`, every table is a case-sensitive quoted name
- **Cleaning stream names.** Only raise this if the actual stream names are messy (spaces, dashes, dots or file extensions such as `Flights.xlsx` or `Feedback form - Answers`). Suggest the fewest steps that fix the names you see, for example `{{ stream_name | replace(" ", "_") | replace("-", "_") | upper }}`, and keep the template simple. Don't offer a long filter chain by default
- **Branches.** Check whether branching is on for the sync (see `references/branching.md`). If it's on, flag that branches will clash without `{{branch_name}}` and recommend the fix. If it's off, flag it once and move on
- **More than one sync per plugin or source.** Ask whether the user has, or expects, several syncs from the same plugin (several accounts, environments or test syncs). Layouts keyed only on plugin and stream, such as "schema per plugin, table = stream", only stay unique with one sync per plugin. Raise this before the preview rather than letting the preview find it

##### 4. Confirm how it generalises
One example can fit more than one rule. Where it's ambiguous, ask with `ask_user_question`. For example: "`ORDERS` came from `Orders`. Should names always be uppercased?" or "Is `ANALYTICS` fixed, or should it change per plugin?" In Fork A, ask for or construct examples from more than one plugin or sync, since one example rarely pins down a rule for everything.

##### 5. Explain where names would clash
Before the preview, tell the user in plain language which situations would make two streams land on the same name under their layout. For example, for "schema per plugin, table = stream":
- A second sync from the same plugin with an overlapping stream (two Jira syncs both produce `OMNATA.JIRA.ISSUES`)
- The same plugin connected to two accounts or environments
- Two stream names that only differ by characters the clean-up removes (`Order-Lines` and `Order Lines`)

Then offer the ways to avoid each one: add the sync to the schema or table name, prefix the tables, hard-code names for the clashing syncs (Fork B only), or accept the risk (see "Accepting clash risk").

Then go to the preview loop. Seeing every stream rendered is the real confirmation; let the user react to the names and adjust.

#### Guided questions (fallback and checklist)

Use these in order when the user says "guide me". Otherwise use them as the checklist for step 3 above. Ask with `ask_user_question`, and stop once the layout is fully settled. Adapt the examples to the plugin; the SQL Server examples show the multi-level case.

1. **Where should normalized data be queried from?**
   - One database for everything
   - A database per source database (database-style sources only)
   - Their own existing database or schema (ask for the name)
2. **How should schemas be split?** Offer only the options that fit the answer to question 1:
   - One schema per plugin or source system, for example `SQLSERVER` or `{{ plugin_id | upper }}`
   - One schema per source database, for example `ADVENTUREWORKS`
   - One schema per source database and schema, for example `ADVENTUREWORKS_DBO`. This is the closest to the source structure
   - One schema per Omnata sync, using `{{sync_slug}}`
3. **How should tables be named?**
   - The source table name only, for example `ORDERS`. This is only safe if the schema split already makes names unique
   - Prefixed with the database, schema or sync, for example `ADVENTUREWORKS_DBO_ORDERS`. Use this when everything lands in one schema
   - The source name as-is, without `upper`. This is case-sensitive, so warn about quoting
4. **Raw tables:** the same database as normalized, or a separate one? Raw tables are internal to Omnata, so a separate raw schema is the common choice. Keep `{{sync_slug}}` in `raw_object` unless the schema split already guarantees uniqueness.
5. **Branches:** is branching on for the sync (see `references/branching.md`)? If it's on, see "Branches" under Patterns.
6. **Column names:** as in the source, uppercased, or cleaned up (`transliterate`, `fivetran_word_division`, `prepend_starting_number_with_underscore`)?
7. **Exceptions:** does any connection, database or schema need different handling? Examples:
   - Two Omnata connections pointing at different servers that both have a database called `Sales`
   - One database that should land somewhere special

#### Patterns

These are suggested layouts, not engine features. Use them as a reference when writing the Jinja and as suggestions when the user asks to be guided. Don't present them as a menu the user must choose from.

| Layout | Pattern |
|---|---|
| One database, schema per plugin | **P1** |
| One database, schema per source database and schema | **P2** |
| Database per source database | **P3** |
| Schema per sync | **P4** |
| Same name on two servers, or other exceptions | **P5** (hard-code, Fork B only) or **P6** (conditional) |

The examples use SQL Server `sync_parameters` and placeholder database names `ACME_RAW` and `ACME_ANALYTICS`. Replace them with the user's names.

##### P1: One schema per plugin, tables prefixed
The tables are prefixed because every source database and schema shares one Snowflake schema.
```sql
OBJECT_CONSTRUCT(
  'raw_database',        'ACME_RAW',
  'raw_schema',          'SQLSERVER',
  'raw_object',          '{{ sync_slug | replace("-", "_") | upper }}_{{ stream_name | upper }}',
  'normalized_database', 'ACME_ANALYTICS',
  'normalized_schema',   'SQLSERVER',
  'normalized_object',   '{{ sync_parameters.database | upper }}_{{ sync_parameters.schema | upper }}_{{ stream_name | upper }}'
)
```
`AdventureWorks.dbo.OrderLines` renders as `ACME_ANALYTICS.SQLSERVER.ADVENTUREWORKS_DBO_ORDERLINES`

##### P2: One schema per source database and schema
The closest to the source structure. Table names stay short.
```sql
OBJECT_CONSTRUCT(
  'raw_database',        'ACME_RAW',
  'raw_schema',          'SQLSERVER',
  'raw_object',          '{{ sync_slug | replace("-", "_") | upper }}_{{ stream_name | upper }}',
  'normalized_database', 'ACME_ANALYTICS',
  'normalized_schema',   '{{ sync_parameters.database | upper }}_{{ sync_parameters.schema | upper }}',
  'normalized_object',   '{{ stream_name | upper }}'
)
```
`AdventureWorks.dbo.OrderLines` renders as `ACME_ANALYTICS.ADVENTUREWORKS_DBO.ORDERLINES`

##### P3: One Snowflake database per source database
```sql
OBJECT_CONSTRUCT(
  'raw_database',        'ACME_RAW',
  'raw_schema',          'SQLSERVER',
  'raw_object',          '{{ sync_slug | replace("-", "_") | upper }}_{{ stream_name | upper }}',
  'normalized_database', 'SQLSERVER_{{ sync_parameters.database | upper }}',
  'normalized_schema',   '{{ sync_parameters.schema | upper }}',
  'normalized_object',   '{{ stream_name | upper }}'
)
```
`AdventureWorks.dbo.OrderLines` renders as `SQLSERVER_ADVENTUREWORKS.DBO.ORDERLINES`. One Snowflake database is created per source database.

##### P4: One schema per sync
The simplest option, and it's always unique. Works for any plugin.
```sql
OBJECT_CONSTRUCT(
  'raw_database',        'ACME_RAW',
  'raw_schema',          '{{ plugin_id | upper }}',
  'raw_object',          '{{ sync_slug | replace("-", "_") | upper }}_{{ stream_name | upper }}',
  'normalized_database', 'ACME_ANALYTICS',
  'normalized_schema',   '{{ sync_slug | replace("-", "_") | upper }}',
  'normalized_object',   '{{ stream_name | upper }}'
)
```
With the slug `acme-sqlserver-sales-dbo`, the table renders as `ACME_ANALYTICS.ACME_SQLSERVER_SALES_DBO.ORDERLINES`

##### P5: Hard-code a value for a specific sync (Fork B only)
Use this when variables can't tell two syncs apart. For example, two Omnata connections on different servers each have a database called `Sales`. P2 would render both to `SALES_DBO` and collide.

Give each affected sync its own location with a fixed value:
```sql
-- sync for server 1
'normalized_schema', 'SALES_AU_DBO'
-- sync for server 2
'normalized_schema', 'SALES_NZ_DBO'
```
Alternatively, put a distinguishing token in the sync slug and keep one template, as in P4.

##### P6: Conditional template (use sparingly)
One template that handles exceptions with `{% if %}`. Use it only when the exceptions are few and stable. Every new exception means editing the template.
```sql
'normalized_schema',
'{%- if sync_parameters.database == "AdventureWorks" -%}SALES{%- else -%}{{ sync_parameters.database | upper }}{%- endif -%}_{{ sync_parameters.schema | upper }}'
```
- Use `{%-` and `-%}` so no whitespace leaks into the rendered name
- Comparisons are case-sensitive, so match the exact source value

##### Branches (only for syncs with branching on)
Each branch of a sync gets its own tables but shares the sync's one template (Omnata docs, Branching > Inbound Sync branching). The patterns above don't include `{{branch_name}}`, so if a sync has branches, they would land on the same tables.

For how branching works, and how to tell whether a sync has branching on, see `references/branching.md`. For an existing sync, check rather than ask. For a new sync, use the answer given during sync configuration.

If branching is off, nothing needs to change. Flag it once if the template has no `{{branch_name}}`: "If you create a branch of this sync later, table names will clash. Add the branch name to the template before you do."

If branching is on, flag the clash and recommend:
1. Add `{{ branch_name | upper }}` to `raw_object`, for example `'{{ sync_slug | replace("-", "_") | upper }}_{{ branch_name | upper }}_{{ stream_name | upper }}'`. Raw tables are internal, so this costs nothing
2. Choose how a branch shows up in the normalized views:

| Goal | Example `normalized_object` or `normalized_schema` | Renders as (main / `test` branch) |
|---|---|---|
| **Main keeps clean names, branches get a suffix** (usual choice) | `normalized_object`: `'{{ stream_name | upper }}{% if branch_name != "main" %}_{{ branch_name | upper }}{% endif %}'` | `ORDERS` / `ORDERS_TEST` |
| **Separate schema per branch** | `normalized_schema`: `'SQLSERVER_{{ branch_name | upper }}'` | `SQLSERVER_MAIN.ORDERS` / `SQLSERVER_TEST.ORDERS` |
| **Production and test environments** (from the docs) | `normalized_database`: `'{% if branch_name == "main" %}PRODUCTION{% else %}TEST{% endif %}'` | `PRODUCTION...` / `TEST...` |

- A per-branch schema or database creates a new schema for each new branch name, which must be set up first (see "New schemas later")
- The production/test condition maps every non-main branch to the same place, so two open branches of one sync collide in `TEST`. Keep `{{branch_name}}` in the object name too if more than one branch can be open
- The suffix option is the easiest to add later: main's names don't change, so it can be added when the user starts branching without breaking anything downstream

##### Column options (any pattern)
| Goal | `normalized_column` |
|---|---|
| Keep the source names, case-sensitive | `{{column_name}}` (default) |
| Uppercase | `{{ column_name | upper }}` |
| Cleaned up | `{{ column_name | transliterate | fivetran_word_division | multiple_underscores_to_single | prepend_starting_number_with_underscore | upper }}` |

#### Loading existing syncs

Both forks check new locations against the syncs that already exist:
```sql
SELECT SYNC_SLUG, PLUGIN_FQN, SYNC_PARAMETERS,
       OBJECT_KEYS(INBOUND_STREAMS_CONFIGURATION:included_streams) AS STREAMS,
       INBOUND_STORAGE_CONFIGURATION, BRANCHING_MODE_ENABLED
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_DIRECTION = 'inbound';

-- open branches, so each one is rendered too
SELECT s.SYNC_SLUG, b.BRANCH_NAME, b.BRANCH_STATE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_BRANCH b
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC s ON s.SYNC_ID = b.SYNC_ID
WHERE s.SYNC_DIRECTION = 'inbound';
```
In the preview plan, add each one with `"existing": true` and its `INBOUND_STORAGE_CONFIGURATION` as its own `storage_location` (empty if NULL). Derive `plugin_id` from `PLUGIN_FQN`. Give each sync with open branches `"branches": ["main", <its open branches>]`.

`BRANCHING_MODE_ENABLED` shows whether a sync has branching on (see `references/branching.md`). If a sync has branching on but no `{{branch_name}}` in its stored template, mention it.

#### Preview, check, iterate

1. Build a plan JSON listing the syncs to check: their slug, `sync_parameters` and stream names. Put the shared template in the top-level `storage_location`, and any per-sync location in that sync's own `storage_location`. Set `plugin_id` at the top level, or per sync when plugins are mixed. Add existing syncs as described above. If branching is on for the planned syncs, set a top-level `"branches": ["main", "test"]` so every planned sync is also rendered on a hypothetical branch; this proves branches don't collide with main. When writing into a database that already holds objects, add them as `"existing_tables": ["DB.SCHEMA.TABLE", ...]` (exact case, from `INFORMATION_SCHEMA.TABLES`).
2. Run the preview. Tell the user first that this runs a local Python script from the skill, which only reads `plan.json` and prints the preview; it doesn't connect to Snowflake or change anything:
   ```bash
   python3 <plugin_dir>/scripts/render_storage_location.py plan.json
   ```
   It renders the raw and normalized path for every stream with the engine's own filters, and lists any problems:
   - Collisions
   - Custom schemas in the app database
   - Lowercase, case-sensitive names
   - Paths that match an object already in the account, when `existing_tables` is given

   It also returns `schemas_needed`: every database and schema the planned syncs render to, used to create the location
3. Show the user:
   - A table of `sync / stream / raw path / normalized path` (a sample, if there are many streams)
   - A sample column name
   - Any problems the preview found
4. Ask with `ask_user_question`:
   - **Accept:** apply it (see the fork's last step)
   - **Adjust:** change one part (a database, schema or table naming choice, or an exception), then re-render
   - **Start again:** go back to the open prompt
5. Resolve every collision the preview reports, or have the user accept it under "Accepting clash risk".

#### Accepting clash risk

The user may choose a simpler layout and accept the risk of clashes. What can be accepted depends on what collides:

| Collision | What happens | Can it be accepted? |
|---|---|---|
| **Normalized view**, between real syncs | Views are created with `create or replace view`, so whichever sync runs last replaces the other's view, and the views keep flipping between them. Raw data is intact | Yes, if the user understands one sync's view will be missing at any time. Usually better avoided, since it's confusing to query |
| **A future branch on main's tables** (branching off today, template has no `{{branch_name}}`) | Nothing unless a branch of the sync is created later | Yes. Flag it once; the fix is in "Branches" |
| **Possible future clash** (a second sync from the same plugin, a new environment) | Nothing yet | Yes. Record the risk so it's checked when that sync is configured |
| **Raw table**, between real syncs or between open branches | Both write to one table without any ownership check, which corrupts both | **No.** Keep `{{sync_slug}}` (and `{{branch_name}}` if branching is on) in `raw_object`, or otherwise make raw names unique. This is cheap, since raw tables are internal |
| **Raw table matches a leftover table** (from a deleted sync, flagged by `existing_tables`) | The engine reuses it silently, so the old rows are mixed in with the new sync's data | Only if the user confirms the old data should be kept. Otherwise change the raw name, or have the user drop the leftover table first |
| **Normalized view matches an existing view** | The sync replaces it with `create or replace view` | Yes, if the existing view is a leftover. Check it isn't a user-built view first |

When the user accepts a risk:
- Restate exactly which situations will clash, and get an explicit yes with `ask_user_question`
- In Fork A, tell them the risk applies to every future sync, and that Fork B overrides can fix individual clashes later
- In Fork B, re-run the preview at B1 for every later sync. If a clash is about to become real, say so before configuring that sync

`transliterate` uses `unidecode` in the engine. If it isn't installed locally, the script uses a close approximation, so names with non-ASCII characters may render slightly differently. `RESOLVE_TARGET_TABLE_PATH` isn't exposed in the installed app, which is why the preview runs locally.

#### Creating the location and privileges

Omnata recommends one setup for any custom location: **managed access schemas owned by a database role** that is granted to the app. Source: Omnata docs, Inbound > Permission Strategies > "Strategy 3: Managed access schema (recommended)". Use this setup; don't offer the alternatives (the app owning the whole database, or owning schemas it creates) unless the user asks for them.

Why: the sync engine must own the normalized views so it can recreate them when the source schema changes (a view definition can't be altered after creation). A database role is the only way to share ownership with an application, so the user's admins and the app both control the objects.

##### What to create
Take the `schemas_needed` list from the final preview. It lists every database and schema the planned syncs render to, and whether each holds raw tables, normalized views, or both. For each database, generate:

```sql
-- once per database
CREATE DATABASE IF NOT EXISTS <DB>;
CREATE DATABASE ROLE IF NOT EXISTS <DB>.OMNATA_ROLE;
GRANT DATABASE ROLE <DB>.OMNATA_ROLE TO APPLICATION OMNATA_SYNC_ENGINE;
-- so the admin running this can see and manage the objects (use their current role)
GRANT DATABASE ROLE <DB>.OMNATA_ROLE TO ROLE <ADMIN_ROLE>;

-- once per schema
CREATE SCHEMA IF NOT EXISTS <DB>.<SCHEMA> WITH MANAGED ACCESS;
GRANT OWNERSHIP ON SCHEMA <DB>.<SCHEMA> TO DATABASE ROLE <DB>.OMNATA_ROLE;
-- schemas that hold raw tables
GRANT OWNERSHIP ON FUTURE TABLES IN SCHEMA <DB>.<SCHEMA> TO DATABASE ROLE <DB>.OMNATA_ROLE;
-- schemas that hold normalized views
GRANT OWNERSHIP ON FUTURE VIEWS IN SCHEMA <DB>.<SCHEMA> TO DATABASE ROLE <DB>.OMNATA_ROLE;
```
- Database roles belong to one database, so each database gets its own `OMNATA_ROLE`. The name is a convention from the docs; use the user's name if they have one
- A schema holding both tables and views (raw and normalized side by side) gets both future grants
- Use the exact case from the preview. If a schema name isn't all uppercase, quote it

##### Reuse an existing role
Before generating anything, check whether the database already has the role and whether it's granted to the app:
```sql
SHOW DATABASE ROLES IN DATABASE <DB>;
SHOW GRANTS OF DATABASE ROLE <DB>.OMNATA_ROLE;   -- look for APPLICATION OMNATA_SYNC_ENGINE
```
If it exists and is granted to the app, skip the per-database statements and only generate the per-schema ones.

##### Existing databases and schemas
If a schema already exists (for example when landing in a database like `DEMO_DATA`), check it before generating anything:
```sql
SHOW SCHEMAS LIKE '<SCHEMA>' IN DATABASE <DB>;   -- owner, and "options" shows MANAGED ACCESS
SHOW FUTURE GRANTS IN SCHEMA <DB>.<SCHEMA>;
```
- Already managed access and owned by the database role: nothing to do
- Otherwise, converting it (`ALTER SCHEMA ... ENABLE MANAGED ACCESS`, transferring ownership) changes how grants work for everything already in it, including user objects. Show the user what's there and ask before changing it. Creating a new schema is usually the better choice
- Leftover Omnata tables or views owned by another role won't be manageable by the app. Have the user drop them, or transfer their ownership to the database role

##### Running it
- Run the statements one at a time, in the order shown: transfer schema ownership first, then add the future ownership grants. Snowflake rejects an ownership transfer while ownership future grants exist in the schema. If it fails for that reason, revoke the future grants, transfer ownership, then grant them again
- **Show the full script, explain what each statement does, and confirm with `ask_user_question` before running any of it.** It creates schemas and a database role, transfers schema ownership and grants privileges to the app
- If the user's current role can create databases (or owns the target database) and can grant to the application, CoCo can run it. Otherwise hand the script to their Snowflake admin and wait until it's done
- Verify afterwards:
  ```sql
  SHOW GRANTS TO DATABASE ROLE <DB>.OMNATA_ROLE;
  SHOW FUTURE GRANTS IN SCHEMA <DB>.<SCHEMA>;
  ```

##### New schemas later
Because the app can't create schemas under this setup, a template that renders new schemas over time (`{{ plugin_id }}`, `{{ sync_slug }}` or `{{ branch_name }}` in a schema name) needs this setup run again before each sync that introduces a new schema:
- **Fork B:** CoCo does this at B4 for every sync, using that sync's preview
- **Fork A:** the default applies to syncs created later, often in the UI, where nobody runs the setup first. Tell the user this when they choose a variable schema name, and suggest fixed schema names (for example `RAW` and `NORMALIZED`, with variables only in table names) unless they're happy to pre-create schemas for each new plugin or sync

##### What the app grants itself
The app grants `SELECT` to its `OMNATA_ADMINISTRATOR` app role on every object it creates. It recreates views with `copy grants`, so grants made on a view survive recreates.

##### Giving people read access
Offer this if the user asks who can query the data. Readers only need the normalized views:
```sql
GRANT USAGE ON DATABASE <DB> TO ROLE <READER_ROLE>;
GRANT USAGE ON SCHEMA <DB>.<NORMALIZED_SCHEMA> TO ROLE <READER_ROLE>;
GRANT SELECT ON ALL VIEWS IN SCHEMA <DB>.<NORMALIZED_SCHEMA> TO ROLE <READER_ROLE>;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA <DB>.<NORMALIZED_SCHEMA> TO ROLE <READER_ROLE>;
```
- The schemas are managed access, so these grants must come from the schema owner (a role that has `OMNATA_ROLE`) or a role with `MANAGE GRANTS`
- No grants are needed on the raw schema
- To test as the reader, run `USE ROLE <READER_ROLE>; USE SECONDARY ROLES NONE;` first. Otherwise secondary roles (`ALL` by default) can make the test pass when it shouldn't

### Fork A: Develop a naming system with the custom default template

Goal: one template that every future sync can use as-is, with no overrides. It's the same setting as Settings > Data Management in the UI.

#### A1: Check what's set today
Read the current custom default (query above). If one is set, show it so the user can build on it or replace it.

#### A2: Design the template
Follow "Capturing the design", with these limits:
- **Fully variable-driven.** The template applies to every future sync from every plugin, so P5 isn't available. Prefer patterns that only use `stream_name`, `sync_slug`, `branch_name` and `plugin_id` (P4, or P1 with `{{ plugin_id | upper }}`)
- `sync_parameters.<key>` differs per plugin and renders blank when missing, so only use it inside an `{% if plugin_id == "..." %}` block (P6)
- If the user's exceptions can't be expressed with variables, say so. The options are to accept a less specific template, or to switch to Fork B for those syncs

#### A3: Preview against existing and future syncs
Run the preview loop with:
- **All existing inbound syncs** on their stored locations. Existing syncs don't move, but the new default can render onto their tables
- **Hypothetical future syncs** that use the new template, for example a second sync from each plugin with the same streams, and one per plugin the user plans to add. This proves the template stays unique as syncs are added

#### A4: Apply
First create the location and privileges for every schema in the preview's `schemas_needed` (see "Creating the location and privileges"). `SET_DEFAULT_INBOUND_STORAGE_LOCATION` checks the location by creating test objects, so it fails if this hasn't been done.

Then confirm with the user, since it affects every future sync:
```sql
CALL OMNATA_SYNC_ENGINE.API.SET_DEFAULT_INBOUND_STORAGE_LOCATION(
  OBJECT_CONSTRUCT(
    'raw_database',        'ACME_RAW',
    'raw_schema',          '{{ plugin_id | upper }}',
    'raw_object',          '{{ sync_slug | replace("-", "_") | upper }}_{{ stream_name | upper }}',
    'normalized_database', 'ACME_ANALYTICS',
    'normalized_schema',   '{{ sync_slug | replace("-", "_") | upper }}',
    'normalized_object',   '{{ stream_name | upper }}'
  )
);
```
The handler validates the location by creating and dropping a test raw table and view, so it fails early if the app lacks privileges. It returns `{"success": false, "error": ...}` rather than raising, so always read the result. Passing NULL clears the custom default.

Then tell the user:
- Existing syncs won't move
- New syncs created in the UI pick up the template automatically
- Syncs created with `CONFIGURE_OMNATA_INBOUND_SYNC` only use it if it's passed explicitly as `INBOUND_STORAGE_LOCATION`. CoCo does this when configuring syncs

### Fork B: Override the location per sync

Goal: set each sync's own `INBOUND_STORAGE_LOCATION`, with CoCo keeping the naming consistent across syncs instead of relying on one overall template. Hard-coded values (P5) are allowed.

#### B1: Load existing syncs
Load the existing syncs (see "Loading existing syncs"). Check whether they follow a recognisable convention (the same databases and schema pattern), so it can be offered in the open prompt.

#### B2: Design
Follow "Capturing the design". The user can also name a specific sync whose location to reuse. All patterns are available. Prefer variables where they work, so the same location can be reused for the next sync, and use P5 hard-coded values only for the syncs variables can't separate.

#### B3: Preview against existing and planned syncs
Run the preview loop with:
- The sync or syncs being configured, each with its override as its own `storage_location`
- **All existing inbound syncs** on their stored locations, since an override can collide with any of them

#### B4: Apply
First create the location and privileges for this sync's `schemas_needed` (see "Creating the location and privileges"). Skip any schema that already exists with the right setup.

Then pass the accepted object as `INBOUND_STORAGE_LOCATION` when calling `CONFIGURE_OMNATA_INBOUND_SYNC` (`references/configure-syncs.md`). When configuring many syncs in one go, preview them all together before creating any.

**Changing an existing sync's location** (re-send its full configuration, or use `SET_INBOUND_SYNC_LOCATION` in `references/sync-management.md`):
- It takes effect at the next run. Until then the stored location (`INBOUND_STORAGE_CONFIGURATION`) changes, but the applied location (`INBOUND_STORAGE_LOCATION_APPLIED`) doesn't
- That run moves the existing tables and views (it doesn't copy them) and deletes the old ones. Open branches move too
- Suggest one run straight away to confirm the move
- Tables from streams the sync no longer uses stay in the old location. Look for them afterwards and offer to drop them

For the next sync, start at B1 again. The convention now includes this sync.

### Stopping points

- After Step 1 (intent), including the app default, custom default or custom for this sync question when configuring a sync
- After the open prompt, and after each gap or generalisation question
- After each preview, before accepting
- Before running the location and privileges script
- Before calling `SET_DEFAULT_INBOUND_STORAGE_LOCATION`, since it affects every future sync
