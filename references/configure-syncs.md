<!-- owner: cortex-code -->
---
name: omnata-configure-syncs
description: "Create or update Omnata syncs programmatically via CONFIGURE_OMNATA_OUTBOUND_SYNC or CONFIGURE_OMNATA_INBOUND_SYNC. Use when: user wants to configure an inbound or outbound sync, create a new sync, manage sync config in source control, deploy syncs via CI/CD, manage test/prod environments, bulk-configure streams, or create a sync to Slack or another plugin. Triggers: configure sync, create inbound sync, create outbound sync, create a sync to Slack, create a sync to Salesforce, create a sync to HubSpot, CONFIGURE_OMNATA_OUTBOUND_SYNC, CONFIGURE_OMNATA_INBOUND_SYNC, deploy sync, notification sync, bulk configure, bulk streams, configure sync from file, create sync with streams, add many streams, programmatic sync setup, source control sync, CI/CD sync, test prod sync."
---

# Configure Syncs

Create or update syncs programmatically using stored procedures. This reference covers:

- **Outbound syncs** (push data from Snowflake to an external app) -- organized by plugin
- **Inbound syncs** (pull data from an external app into Snowflake) -- procedure reference, examples, and use-case workflows

Both procedures are **idempotent**: if the `sync_slug` already exists they update the sync;
otherwise they create a new one.

## Prerequisites

- Active Snowflake connection with the `OMNATA_ADMINISTRATOR` application role
- An existing Omnata connection to the target plugin (identified by `connection_slug`)
- For outbound: the source table/view must exist and be granted SELECT to `OMNATA_SYNC_ENGINE`

---

# Outbound Syncs

## Outbound Workflow

### Step 1: Find Existing Syncs to the Target Plugin

The configuration JSON structures are plugin-specific and best understood by inspecting
an existing sync. **You must always check for existing syncs to the target plugin first.**

```sql
SELECT
    S.SYNC_ID,
    S.SYNC_NAME,
    S.SYNC_SLUG,
    S.SYNC_PARAMETERS::VARCHAR AS SYNC_PARAMETERS,
    S.OUTBOUND_FIELD_MAPPINGS::VARCHAR AS FIELD_MAPPINGS,
    S.OUTBOUND_SYNC_STRATEGY::VARCHAR AS SYNC_STRATEGY,
    S.SYNC_SCHEDULE::VARCHAR AS SYNC_SCHEDULE,
    S.OUTBOUND_SOURCE_DATABASE,
    S.OUTBOUND_SOURCE_SCHEMA,
    S.OUTBOUND_SOURCE_TABLE,
    S.OUTBOUND_SOURCE_ID_COLUMN,
    C.CONNECTION_SLUG
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC S
JOIN OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION C ON S.CONNECTION_ID = C.CONNECTION_ID
WHERE S.SYNC_DIRECTION = 'outbound'
  AND C.PLUGIN_FQN ILIKE '%<PLUGIN_NAME>%'
ORDER BY S.SYNC_NAME;
```

Replace `<PLUGIN_NAME>` with the target (e.g. `SLACK`, `SALESFORCE`, `HUBSPOT`).

**If no syncs exist to this plugin:** Advise the user that they need to create at least
one sync to this destination via the Omnata UI first. The UI-created sync serves as the
template configuration that this procedure can then clone and modify. Without an existing
sync, the exact JSON structures for `sync_parameters` and `sync_strategy` cannot be
reliably determined.

**If syncs exist:** Pull the full definition of the most similar sync and use it as a
template. Ask the user which existing sync is closest to what they want to create.

---

### Step 2: Prepare Source Table

The source table or view must:
1. Exist in Snowflake
2. Have SELECT granted to the Omnata application
3. Have a non-nullable unique identifier column (the `id_column`)

```sql
GRANT SELECT ON VIEW <database>.<schema>.<table> TO APPLICATION OMNATA_SYNC_ENGINE;
```

**Common pitfall:** If the ID column can contain NULL values, the sync will fail with
`NULL identifier(s) found`. Use `COALESCE` or ensure NULLs are impossible in the ID
column definition.

---

### Step 3: Call CONFIGURE_OMNATA_OUTBOUND_SYNC

The procedure uses **named parameters** for easier handling of optional parameters. All OBJECT parameters can be constructed using `OBJECT_CONSTRUCT(key1,value1,key2,value2)` or `PARSE_JSON($${}$$)`.

#### Procedure Signature

See https://docs.omnata.com/omnata-product-documentation/omnata-sync-for-snowflake/how-it-works/internal-stored-procedures for parameter example values.

| Name | Type | Required | Description |
|---|---|---|---|
| `sync_slug` | VARCHAR | Yes | Kebab-case identifier. If exists, updates instead of creating. |
| `sync_name` | VARCHAR | Yes | Human-readable display name |
| `connection_slug` | VARIANT | Yes | The connection slug for a sync or branch. Can be either a string (simple sync) or an object (multi-account or branching). In either case, always cast to VARIANT |
| `sync_parameters` | OBJECT | Yes | Plugin-specific parameters (see plugin sections below) |
| `sync_schedule` | OBJECT | Yes | Schedule configuration |
| `sync_strategy_name` | VARCHAR | Yes | Strategy name (plugin-specific, see plugin sections below) |
| `field_mappings` | OBJECT | Yes | Field mapping or Jinja template configuration |
| `source_table` | OBJECT | Yes | Source table reference (database, schema, table, id_column) |
| `sync_tuning_parameters` | OBJECT | No | Tuning parameters (default NULL) |
| `sync_tags` | ARRAY | No | Tags (default []) |
| `multi_account` | BOOLEAN | No | Multi-account mode (default FALSE) |
| `single_account_branching` | BOOLEAN | No | Enable branching (default FALSE) |
| `branch_only_sync_parameters` | OBJECT | No | Branch-specific parameters (default NULL) |
| `outbound_target_type` | VARCHAR | No | Target type override (default NULL) |
| `single_account_branch_to_configure` | VARCHAR | No | Branch name e.g. 'dev' (default NULL) |
| `single_environment_branching_mode` | VARCHAR | No | Branching mode (default NULL) |
| `branch_outbound_record_state_behaviour` | VARCHAR | No | Default 'START_EMPTY' |
| `branch_reopen_behaviour` | VARCHAR | No | Default 'CONTINUE' |
| `branch_outbound_branch_record_filter` | OBJECT | No | Branch record filter (default NULL) |
| `raise_errors` | BOOLEAN | No | Whether to raise errors (default FALSE, meaning 'success' flag and 'data'/'error' flags are returned) |
| `current_user` | VARCHAR | No | Override current user (default NULL) |

#### Common Parameters (All Plugins)

**Schedule options:**

| Schedule type | Configuration |
|---|---|
| Manual only | `OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', 'COMPUTE_WH')` |
| Every 15 mins | `OBJECT_CONSTRUCT('mode', 'snowflake_task', 'sync_frequency', '15', 'warehouse', 'COMPUTE_WH')` |
| Cron expression | `OBJECT_CONSTRUCT('mode', 'snowflake_task', 'sync_frequency', '0 9 * * * America/New_York', 'sync_frequency_name', 'Custom', 'time_limit_mins', 240, 'warehouse', 'COMPUTE_WH')` |

**Source table:**

```sql
OBJECT_CONSTRUCT(
    'database', '<DATABASE>',
    'schema', '<SCHEMA>',
    'table', '<TABLE_OR_VIEW>',
    'id_column', '<UNIQUE_ID_COLUMN>'
)
```

---

### Step 4: Resume and Run

After creation, the sync starts in `PENDING` state. Resume it to activate the schedule,
then optionally trigger an immediate run:

```sql
-- Activate the schedule
CALL OMNATA_SYNC_ENGINE.API.RESUME_SYNC('<sync_slug>', 'main');

-- Trigger immediate run
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(
    NULL, '<sync_slug>', 'main', 'external',
    OBJECT_CONSTRUCT('triggered_by', 'cortex_code'), FALSE
);
```

---

### Step 5: Verify

```sql
SELECT SYNC_ID, SYNC_NAME, HEALTH_STATE, RUN_STATE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC
WHERE SYNC_SLUG = '<sync_slug>';

SELECT SYNC_RUN_ID, HEALTH_STATE, GLOBAL_ERROR, OUTBOUND_TOTAL_COUNT,
    OUTBOUND_APPLY_STATE_COUNTS::VARCHAR AS APPLY_COUNTS
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN
WHERE SYNC_ID = (SELECT SYNC_ID FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_SLUG = '<sync_slug>')
ORDER BY RUN_START_DATETIME DESC LIMIT 1;
```

---

## Outbound Plugin: Slack

### Strategy

- **Strategy name:** `'Post Message'`
- **Behaviour:** Posts a message into a Slack channel on record create. Does not act on update/delete/unchanged.

### Sync Parameters

The `sync_parameters` must include the target channel:

```sql
OBJECT_CONSTRUCT(
    'channel', OBJECT_CONSTRUCT(
        'value', '<channel-name>',
        'metadata', OBJECT_CONSTRUCT(
            'id', '<SLACK_CHANNEL_ID>',
            'name', '<channel-name>',
            'is_channel', TRUE
        )
    )
)
```

Get the channel ID and name from an existing Slack sync's `SYNC_PARAMETERS`.

### Field Mappings (Jinja Template)

Slack syncs use `mapper_type: 'jinja_template'` to compose the message body. The template
has access to `row['COLUMN_NAME']` for each column in the source table.

```sql
OBJECT_CONSTRUCT(
    'mapper_type', 'jinja_template',
    'jinja_template', '{{ row[''FIRST_NAME''] }} {{ row[''LAST_NAME''] }} ({{ row[''EMAIL''] }}) from {{ row[''ORGANIZATION''] }}.\nInstalled {{ row[''PRODUCT_NAME''] }} in {{ row[''ACCOUNT''] }} ({{ row[''REGION''] }}).',
    'additional_column_expressions', OBJECT_CONSTRUCT()
)
```

### Preview the Jinja Template

Before deploying, **always preview the rendered message** so the user can see exactly what
will appear in Slack. Query a sample row from the source table and manually substitute the
column values into the template:

```sql
SELECT * FROM <source_database>.<source_schema>.<source_table> LIMIT 3;
```

Then render the template by replacing `{{ row['COLUMN'] }}` with the actual values from
a sample row. Present the result to the user as the message that will be posted to Slack,
and confirm it looks correct before proceeding.

### Full Example

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_OUTBOUND_SYNC(
    'my-events-to-slack',
    'My Events to Slack',
    'omnata-slack'::VARIANT,
    OBJECT_CONSTRUCT(
        'channel', OBJECT_CONSTRUCT(
            'value', 'lead-marketing-activity',
            'metadata', OBJECT_CONSTRUCT(
                'id', 'C02EG7V3QJF',
                'name', 'lead-marketing-activity',
                'is_channel', TRUE
            )
        )
    ),
    OBJECT_CONSTRUCT(
        'mode', 'snowflake_task',
        'sync_frequency', '15 5,9,13 * * * Australia/NSW',
        'sync_frequency_name', 'Custom',
        'time_limit_mins', 240,
        'warehouse', 'COMPUTE_WH'
    ),
    'Post Message',
    OBJECT_CONSTRUCT(
        'mapper_type', 'jinja_template',
        'jinja_template', '{{ row[''FIRST_NAME''] }} {{ row[''LAST_NAME''] }} ({{ row[''CONSUMER_EMAIL''] }}) from {{ row[''CONSUMER_ORGANIZATION''] }}.\nInstalled {{ row[''LISTING_DISPLAY_NAME''] }} in {{ row[''CONSUMER_ACCOUNT_NAME''] }} ({{ row[''SNOWFLAKE_REGION''] }}), account {{ row[''CONSUMER_ACCOUNT_LOCATOR''] }}.',
        'additional_column_expressions', OBJECT_CONSTRUCT()
    ),
    OBJECT_CONSTRUCT(
        'database', 'SCRATCH',
        'schema', 'PRODUCTION',
        'table', 'LISTING_EVENTS_GET',
        'id_column', 'UNIQUE_ID'
    ),
    OBJECT_CONSTRUCT(),
    [],
    FALSE, FALSE, NULL::OBJECT, NULL::VARCHAR, NULL::VARCHAR,
    NULL::VARCHAR, 'START_EMPTY', 'CONTINUE', NULL::OBJECT, FALSE, NULL::VARCHAR
);
```

---

## Outbound Plugin: Salesforce

> **Status:** Supported via this procedure, but no worked example yet. Follow the same
> workflow: pull configuration from an existing Salesforce sync and adapt.

### Strategy Names

- `'Create'` -- insert new records
- `'Update'` -- update existing records (requires APP_IDENTIFIER mapping)
- `'Upsert'` -- create or update based on external ID
- `'Delete'` -- delete records in Salesforce

### Field Mappings

Salesforce syncs typically use `mapper_type: 'field_mapping_selector'` with structured
field-to-field mappings. Inspect an existing sync's `OUTBOUND_FIELD_MAPPINGS` for the
exact structure.

---

## Outbound Plugin: HubSpot

> **Status:** Supported via this procedure, but no worked example yet. Follow the same
> workflow: pull configuration from an existing HubSpot sync and adapt.

### Strategy Names

- `'Create'` -- insert new records
- `'Update'` -- update existing records
- `'Upsert'` -- create or update

### Field Mappings

HubSpot syncs typically use `mapper_type: 'field_mapping_selector'`. Inspect an existing
sync's `OUTBOUND_FIELD_MAPPINGS` for the exact structure.

---

## Outbound: Other Plugins

> **Status:** Not yet documented. For any other plugin, use the same workflow:
>
> 1. Check for existing syncs to that plugin (Step 1)
> 2. If none exist, advise creating one via the Omnata UI first
> 3. Pull the configuration from the UI-created sync
> 4. Adapt and deploy using `CONFIGURE_OMNATA_OUTBOUND_SYNC`
>
> To add documentation for a new plugin, add a new `## Outbound Plugin: <Name>` section
> above this block following the same structure as the Slack section.

---

## Outbound Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `NULL identifier(s) found` | ID column contains NULL values | Fix the source view to ensure ID column is never NULL (use COALESCE) |
| `Invalid argument types` | Used PARSE_JSON instead of OBJECT_CONSTRUCT | Use OBJECT_CONSTRUCT() for all OBJECT parameters |
| `named arguments do not match` | Tried named parameter syntax | Use positional parameters only |
| Sync stays in PENDING | Not resumed after creation | Call RESUME_SYNC |
| HEALTH_STATE = FAILED after run | Check GLOBAL_ERROR in SYNC_RUN | Query the latest run's GLOBAL_ERROR for details |

---

# Inbound Syncs

Create or update inbound syncs programmatically using `CONFIGURE_OMNATA_INBOUND_SYNC`. This procedure is the single entry point for all inbound sync configuration, whether creating a simple sync, bulk-adding streams, or managing test/prod environments.

The procedure is **idempotent**: calling it with an existing `SYNC_SLUG` updates the sync rather than creating a duplicate. It expects the **full configuration** each time. Omitting a stream from `STREAM_NAMES` removes it from the sync.

## Use cases

- **Simple sync creation** -- programmatically create an inbound sync for one or more streams
- **Bulk stream setup** -- configure syncs with many streams (10+) from a file or list
- **Source control and CI/CD** -- store sync configuration in version control and deploy via pipeline
- **Test/prod environment management** -- use branching to manage separate configurations per environment
- **Programmatic management** -- create and maintain many syncs across plugins

## Prerequisites

- Active Snowflake connection with the `OMNATA_ADMINISTRATOR` application role
- An existing Omnata connection to the source plugin (identified by `connection_slug`)

## Procedure reference

Use **named parameters** (`=>`). All OBJECT parameters can be constructed using `OBJECT_CONSTRUCT(key1,value1,key2,value2)` or `PARSE_JSON($${}$$)`.

### Example: manual schedule, single account

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'my-salesforce-inbound',
    SYNC_NAME          => 'Salesforce to Snowflake',
    CONNECTION_SLUG    => 'my-salesforce-connection'::VARIANT,
    STREAM_NAMES       => ['Account', 'Contact', 'Opportunity'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT(
        'mode', 'manual',
        'warehouse', 'COMPUTE_WH',
        'time_limit_mins', 60
    ),
    RAISE_ERRORS       => true
);
```

### Example: hourly scheduled sync

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'hubspot-hourly',
    SYNC_NAME          => 'HubSpot Hourly Inbound',
    CONNECTION_SLUG    => 'hubspot-prod'::VARIANT,
    STREAM_NAMES       => ['contacts', 'companies', 'deals'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT(
        'mode', 'snowflake_task',
        'sync_frequency', '0 * * * *',
        'sync_frequency_name', 'Hourly',
        'warehouse', 'COMPUTE_WH',
        'time_limit_mins', 120
    ),
    RAISE_ERRORS       => true
);
```

### VARIANT parameters

`CONNECTION_SLUG`, `SYNC_STRATEGY`, and `STORAGE_BEHAVIOUR` are typed as `VARIANT` in the proc signature. Always cast string literals with `::VARIANT`:

```sql
CONNECTION_SLUG   => 'my-connection'::VARIANT,
SYNC_STRATEGY     => 'Auto'::VARIANT,
STORAGE_BEHAVIOUR => 'merge'::VARIANT,
```

When passing an object (per-stream overrides), the `OBJECT_CONSTRUCT` return type is already VARIANT-compatible:

```sql
SYNC_STRATEGY => OBJECT_CONSTRUCT(
    'Account', 'Incremental',
    'Contact', 'Full Refresh'
)::VARIANT,
```

### SYNC_STRATEGY values

`SYNC_STRATEGY` accepts a single string applied to all streams, or an object mapping stream names to individual strategies. Values are case-sensitive:

| Value | Meaning |
|---|---|
| `'Auto'` | Engine chooses per stream (prefers Incremental when supported) |
| `'Incremental'` | Only fetches records changed since last run |
| `'Full Refresh'` | Fetches all records every run |

### STORAGE_BEHAVIOUR values

`STORAGE_BEHAVIOUR` accepts a single string or a per-stream object. Values are lowercase:

| Value | Meaning |
|---|---|
| `'merge'` | Upserts on primary key (default) |
| `'append'` | Appends all records, keeping history |
| `'replace'` | Replaces table contents (deprecated, use `'merge'` with Full Refresh strategy instead) |

### SYNC_SCHEDULE structure

For a **single-account sync** (no multi-account, no branching), the schedule is a flat object with `mode` at the top level:

```sql
-- Manual (on-demand only)
SYNC_SCHEDULE => OBJECT_CONSTRUCT(
    'mode', 'manual',
    'warehouse', 'COMPUTE_WH',
    'time_limit_mins', 60
)

-- Scheduled via Snowflake task
SYNC_SCHEDULE => OBJECT_CONSTRUCT(
    'mode', 'snowflake_task',
    'sync_frequency', '0 9 * * * America/New_York',
    'sync_frequency_name', 'Custom',
    'warehouse', 'COMPUTE_WH',
    'time_limit_mins', 240
)
```

The nested form `{"main": {...}, "dev": {...}}` is only used when `MULTI_ACCOUNT` or `SINGLE_ACCOUNT_BRANCHING` is enabled.

Available schedule modes:

| Mode | Required fields | Use case |
|---|---|---|
| `manual` | `warehouse` (optional, null = serverless), `time_limit_mins` | On-demand runs only |
| `snowflake_task` | `sync_frequency`, `sync_frequency_name`, `warehouse`, `time_limit_mins` | Scheduled via Snowflake tasks |
| `dbt` | `dbt_sync_model_name`, `warehouse`, `time_limit_mins` | Triggered by dbt package |
| `dependent` | `selected_sync` (sync ID to depend on), `warehouse`, `time_limit_mins` | Runs after another sync |

For `snowflake_task`, `sync_frequency_name` must be one of: `'1 min'`, `'5 mins'`, `'15 mins'`, `'Hourly'`, `'Daily'`, `'Custom'`.

### Parameter reference

See https://docs.omnata.com/omnata-product-documentation/omnata-sync-for-snowflake/how-it-works/internal-stored-procedures for additional parameter details.

| Name | Type | Required | Description |
|---|---|---|---|
| `sync_slug` | VARCHAR | Yes | Kebab-case identifier. If exists, updates instead of creating. |
| `sync_name` | VARCHAR | Yes | Human-readable display name |
| `connection_slug` | VARIANT | Yes | Connection slug string (cast with `::VARIANT`), or an object keyed by account/branch for multi-account |
| `sync_parameters` | OBJECT | Yes | Plugin-specific parameters. Values can be terse `{'key': 'value'}` or full `{'key': {'value': '...', 'metadata': {}}}` |
| `sync_schedule` | OBJECT | Yes | Schedule configuration (see SYNC_SCHEDULE structure above) |
| `stream_names` | ARRAY | Yes | Stream names to include. Omitting a stream removes it from the sync |
| `sync_strategy` | VARIANT | Yes | `'Auto'`, `'Full Refresh'`, or `'Incremental'` (cast with `::VARIANT`), or a per-stream object |
| `storage_behaviour` | VARIANT | Yes | `'merge'`, `'append'`, or `'replace'` (cast with `::VARIANT`), or a per-stream object |
| `stream_primary_keys` | OBJECT | No | `{"stream": "field"}` or `{"stream": ["f1","f2"]}`. Only needed when the plugin does not define the primary key |
| `stream_cursor_fields` | OBJECT | No | `{"stream": "cursor_field"}`. Only needed when the plugin does not define a default cursor. Missing cursors downgrade Incremental to Full Refresh |
| `sync_tuning_parameters` | OBJECT | No | Plugin tuning parameters (default NULL) |
| `inbound_storage_location` | OBJECT | No | Custom storage location for raw/normalized tables |
| `inbound_full_refresh_schedule` | OBJECT | No | Periodic full refresh schedule |
| `sync_tags` | ARRAY | No | Arbitrary tags (default []). New tags are auto-registered in the UI |
| `multi_account` | BOOLEAN | No | Multi-account mode (default FALSE). Mutually exclusive with `single_account_branching` |
| `single_account_branching` | BOOLEAN | No | Enable branching (default FALSE) |
| `single_account_branch_to_configure` | VARCHAR | No | Branch name, required when `single_account_branching` is true |
| `raise_errors` | BOOLEAN | No | When true, errors throw a SQL exception. When false (default), errors return as `{"success": false, "error": "..."}` |
| `include_new_streams` | BOOLEAN | No | Auto-include new streams the plugin discovers (default FALSE) |
| `new_stream_sync_strategy` | VARCHAR | No | Strategy for auto-included streams (default `'Auto'`) |
| `new_stream_storage_behaviour` | VARCHAR | No | Storage behaviour for auto-included streams (default `'merge'`) |
| `excluded_streams` | ARRAY | No | Streams to exclude when `include_new_streams` is on (default []) |
| `current_user` | VARCHAR | No | Override current user (default NULL) |

### Return value

```json
{
    "success": true,
    "data": {
        "sync_id": 123,
        "sync_branch_id": null,
        "created_sync": true,
        "updated_sync": false,
        "created_branch": false,
        "updated_branch": false
    }
}
```

When `RAISE_ERRORS` is false (default) and an error occurs:

```json
{
    "success": false,
    "error": "Connection with slug my-connection not found"
}
```

### Key behaviours

- **Idempotent**: If the sync slug already exists, the proc updates it (adds/removes streams) rather than creating a duplicate
- **Stream validation**: The plugin calls the live source system to verify each stream exists
- **PK override**: The plugin's source-defined PK takes precedence over what you pass in `stream_primary_keys`
- **Cursor fallback**: If a stream is set to Incremental but has no cursor field (and none is provided), the strategy is automatically downgraded to Full Refresh

## Running and verifying a sync

After creating the sync, trigger a run:

```sql
CALL OMNATA_SYNC_ENGINE.API.RUN_SYNC(
    NULL,                    -- SYNC_ID (null when using slug)
    'my-salesforce-inbound', -- SYNC_SLUG
    'main',                  -- BRANCH_NAME
    'external',              -- RUN_SOURCE_NAME
    OBJECT_CONSTRUCT(),      -- RUN_SOURCE_METADATA
    true,                    -- WAIT_FOR_COMPLETION
    true,                    -- RAISE_ERRORS
    current_user()           -- CURRENT_USER
);
```

Check sync status:

```sql
SELECT
    SYNC_SLUG,
    SYNC_NAME,
    HEALTH_STATE,
    RUN_STATE,
    SYNC_SCHEDULE:mode::VARCHAR AS SCHEDULE_MODE
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_STATUS
WHERE SYNC_SLUG = 'my-salesforce-inbound';
```

## Inbound notes

- The `inbound_storage_location` uses Omnata template variables (`{{column_name}}`, `{{sync_slug}}`, `{{branch_name}}`, `{{stream_name}}`). These are not Snowflake or SQL variables; do not replace them.
- Setting `"mode":"manual"` means the sync will not auto-schedule. The user triggers runs manually or sets a schedule later.
- The `sync_parameters` field is plugin-specific (e.g. NetSuite may not use any, but other plugins may require configuration here).

---

# Use case: Bulk stream configuration

When the endpoint has many streams (10+), building the `STREAM_NAMES` array and `STREAM_PRIMARY_KEYS` object by hand is tedious. This section covers how to gather and process a large stream list before passing it to `CONFIGURE_OMNATA_INBOUND_SYNC`.

**Applicable plugins:** Salesforce, Marketing Cloud, NetSuite, and any other endpoint with many available streams/objects.

## Bulk Step 1: Gather information

Before generating the SQL, collect these from the user:

| Parameter | How to find it |
|---|---|
| **Omnata database name** | Usually `OMNATA_SYNC_ENGINE` -- confirm with `SHOW DATABASES LIKE '%OMNATA%'` |
| **Connection slug** | `SELECT CONNECTION_SLUG, CONNECTION_NAME, PLUGIN_FQN FROM <database>.DATA_VIEWS.CONNECTION` |
| **Stream list** | Ask the user how they want to provide it (see Step 2) |
| **Sync slug** | Kebab-case identifier (e.g. `netsuite-prod-to-snowflake`) -- the user names this |
| **Sync name** | Human-readable (e.g. `NetSuite Production to Snowflake`) |
| **Warehouse** | Which warehouse to use for sync execution |
| **Sync strategy** | `'Auto'` (default), `'Incremental'`, or `'Full Refresh'` (case-sensitive) |
| **Storage behaviour** | `'merge'` (default, upserts on PK) or `'append'` (lowercase) |

## Bulk Step 2: Get the stream list

Ask the user how they'd like to provide the list of streams/tables to sync:

1. **Excel file** (.xlsx) -- read the file, extract table names from the first column
2. **CSV file** -- read and extract from the relevant column
3. **Paste** -- user pastes a list directly into chat (one per line, or comma-separated)
4. **From existing sync** -- copy streams from another sync already configured in the system
5. **From the plugin catalog** -- use the full set of available streams from the connection

### Processing the stream list

- **Remove duplicates**
- **Trim whitespace**
- Store as a JSON array: `["account","department","transaction",...]`

## Bulk Step 3: Build the primary keys object

Build a JSON object mapping each stream name to its primary key column(s):

```json
{"account": ["id"], "department": ["id"], "transaction": ["id"], ...}
```

**Important notes on primary keys:**

- `["id"]` is a safe default for most streams -- if the plugin has a source-defined PK, it will override your value automatically
- Some streams use composite PKs (e.g. transaction line tables may use `["transaction","id"]` or `["journal","line"]`) -- the plugin handles this
- Streams without a source-defined PK **require** an explicit PK or the proc will fail
- After sync creation, always run the PK reconciliation query (Bulk Step 5) to verify

## Bulk Step 4: Execute procedure

Use the procedure reference above with the gathered parameters. For bulk setups, the `STREAM_NAMES` array will be large and the `STREAM_PRIMARY_KEYS` object will have entries for each stream.

## Bulk Step 5: PK reconciliation (post-creation)

After the sync is created, verify the actual PKs assigned. The plugin provides source-defined
PKs that override the `["id"]` placeholder:

```sql
-- Review all assigned PKs
SELECT 
    f.key as stream_name,
    f.value:primary_key_field::VARCHAR as configured_pk,
    f.value:stream:source_defined_primary_key::VARCHAR as source_defined_pk
FROM <OMNATA_DATABASE>.DATA_VIEWS.SYNC s,
    LATERAL FLATTEN(input => s.INBOUND_STREAMS_CONFIGURATION:included_streams) f
WHERE s.SYNC_SLUG = '<SYNC_SLUG>'
ORDER BY configured_pk, stream_name;
```

```sql
-- Streams with non-standard PKs (review these are correct)
SELECT 
    f.key as stream_name,
    f.value:primary_key_field::VARCHAR as configured_pk
FROM <OMNATA_DATABASE>.DATA_VIEWS.SYNC s,
    LATERAL FLATTEN(input => s.INBOUND_STREAMS_CONFIGURATION:included_streams) f
WHERE s.SYNC_SLUG = '<SYNC_SLUG>'
    AND f.value:primary_key_field::VARCHAR != '["id"]'
ORDER BY stream_name;
```

Present the non-`["id"]` streams to the user for review.

## Bulk Step 6: Report results

Present to the user:

1. **Success/failure** of the proc call
2. **Stream configuration summary** from the reconciliation query -- this will show the actually configured cursor field(s) and primary key field for each stream.
3. **Next steps**: trigger the first run (see "Running and verifying a sync" above)

---

# Stopping Points

- After Outbound Step 1 if no existing syncs found (user must create one in UI first)
- After Outbound Step 1 if the user only needed to understand the existing config
- After Outbound Step 3 if the user wants to review the SQL before running
- After Jinja preview (Slack) if the user wants to adjust the message template
- After Outbound Step 5 for full confirmation
- After inbound proc call if the user wants to review the result before running
- After Bulk Step 4 if the user wants to review removed streams before continuing
- After Bulk Step 6 for full confirmation
