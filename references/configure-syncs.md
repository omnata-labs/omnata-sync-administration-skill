<!-- owner: cortex-code -->
---
name: omnata-configure-syncs
description: "Create or update Omnata syncs programmatically via CONFIGURE_OMNATA_OUTBOUND_SYNC or CONFIGURE_OMNATA_INBOUND_SYNC. Use when: user wants to configure an outbound sync, create a new outbound sync, create a sync to Slack or another plugin, or bulk-configure an inbound sync with many streams. Triggers: configure an outbound sync, create a new outbound sync, create a sync to Slack, create a sync to Salesforce, create a sync to HubSpot, CONFIGURE_OMNATA_OUTBOUND_SYNC, CONFIGURE_OMNATA_INBOUND_SYNC, deploy sync, notification sync, bulk configure, bulk streams, configure sync from file, create sync with streams, add many streams, programmatic sync setup."
---

# Configure Syncs

Create or update syncs programmatically using stored procedures. This reference covers:

- **Outbound syncs** (push data from Snowflake to an external app) -- organized by plugin
- **Inbound syncs** (pull data from an external app into Snowflake) -- for bulk stream setup

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

The procedure uses **positional parameters** (named parameters are not supported by the
native app runtime). All OBJECT parameters must be constructed using `OBJECT_CONSTRUCT()`
rather than `PARSE_JSON()` to ensure correct type matching.

#### Procedure Signature (21 parameters)

| Position | Name | Type | Required | Description |
|---|---|---|---|---|
| 1 | `sync_slug` | VARCHAR | Yes | Kebab-case identifier. If exists, updates instead of creating. |
| 2 | `sync_name` | VARCHAR | Yes | Human-readable display name |
| 3 | `connection_slug` | VARIANT | Yes | Connection slug string (cast to VARIANT) |
| 4 | `sync_parameters` | OBJECT | Yes | Plugin-specific parameters (see plugin sections below) |
| 5 | `sync_schedule` | OBJECT | Yes | Schedule configuration |
| 6 | `sync_strategy_name` | VARCHAR | Yes | Strategy name (plugin-specific, see plugin sections below) |
| 7 | `field_mappings` | OBJECT | Yes | Field mapping or Jinja template configuration |
| 8 | `source_table` | OBJECT | Yes | Source table reference (database, schema, table, id_column) |
| 9 | `sync_tuning_parameters` | OBJECT | No | Tuning parameters (default NULL) |
| 10 | `sync_tags` | ARRAY | No | Tags (default []) |
| 11 | `multi_account` | BOOLEAN | No | Multi-account mode (default FALSE) |
| 12 | `single_account_branching` | BOOLEAN | No | Enable branching (default FALSE) |
| 13 | `branch_only_sync_parameters` | OBJECT | No | Branch-specific parameters (default NULL) |
| 14 | `outbound_target_type` | VARCHAR | No | Target type override (default NULL) |
| 15 | `single_account_branch_to_configure` | VARCHAR | No | Branch name e.g. 'dev' (default NULL) |
| 16 | `single_environment_branching_mode` | VARCHAR | No | Branching mode (default NULL) |
| 17 | `branch_outbound_record_state_behaviour` | VARCHAR | No | Default 'START_EMPTY' |
| 18 | `branch_reopen_behaviour` | VARCHAR | No | Default 'CONTINUE' |
| 19 | `branch_outbound_branch_record_filter` | OBJECT | No | Branch record filter (default NULL) |
| 20 | `raise_errors` | BOOLEAN | No | Whether to raise errors (default FALSE) |
| 21 | `current_user` | VARCHAR | No | Override current user (default NULL) |

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

# Inbound Syncs: Bulk Stream Configuration

This section covers creating or updating an inbound sync with a large number of streams
using `CONFIGURE_OMNATA_INBOUND_SYNC`. This is the programmatic alternative to adding
streams one-by-one through the UI.

**Applicable plugins:** Salesforce, Marketing Cloud, NetSuite, and any other endpoint
with many available streams/objects.

## When to Use This

- Endpoint has many streams (10+) and the UI would be tedious
- Customer has a list of record types (from an Excel export, CSV, or their source system)
- Migrating an existing ETL pipeline to Omnata and need to replicate the same set of tables

---

## Inbound Step 1: Gather Information

Before generating the SQL, collect these from the user:

| Parameter | How to find it |
|---|---|
| **Omnata database name** | Usually `OMNATA_SYNC_ENGINE` -- confirm with `SHOW DATABASES LIKE '%OMNATA%'` |
| **Connection slug** | `SELECT CONNECTION_SLUG, CONNECTION_NAME, PLUGIN_FQN FROM <database>.DATA_VIEWS.CONNECTION` |
| **Stream list** | Ask the user how they want to provide it (see Step 2) |
| **Sync slug** | Kebab-case identifier (e.g. `netsuite-prod-to-snowflake`) -- the user names this |
| **Sync name** | Human-readable (e.g. `NetSuite Production to Snowflake`) |
| **Warehouse** | Which warehouse to use for sync execution |
| **Sync strategy** | `Incremental` (default) or `Full Refresh` |
| **Storage behaviour** | `merge` (default, upserts on PK) or `append` |

---

## Inbound Step 2: Get the Stream List

Ask the user how they'd like to provide the list of streams/tables to sync:

1. **Excel file** (.xlsx) -- read the file, extract table names from the first column
2. **CSV file** -- read and extract from the relevant column
3. **Paste** -- user pastes a list directly into chat (one per line, or comma-separated)
4. **From existing sync** -- copy streams from another sync already configured in the system
5. **From the plugin catalog** -- use the full set of available streams from the connection

### Processing the stream list

- **Lowercase all stream names** -- Omnata plugins use lowercase identifiers
- **Remove duplicates**
- **Trim whitespace**
- Store as a JSON array: `["account","department","transaction",...]`

---

## Inbound Step 3: Build the Primary Keys Object

Build a JSON object mapping each stream name to its primary key column(s):

```json
{"account": ["id"], "department": ["id"], "transaction": ["id"], ...}
```

**Important notes on primary keys:**

- `["id"]` is a safe default for most streams -- if the plugin has a source-defined PK, it will override your value automatically
- Some streams use composite PKs (e.g. transaction line tables may use `["transaction","id"]` or `["journal","line"]`) -- the plugin handles this
- Streams without a source-defined PK **require** an explicit PK or the proc will fail
- After sync creation, always run the PK reconciliation query (Step 5) to verify

---

## Inbound Step 4: Execute with Retry-on-Failure

The `CONFIGURE_OMNATA_INBOUND_SYNC` proc validates every stream against the plugin's
catalog by calling the live source system. If any stream doesn't exist, the **entire call
fails** -- it does not do partial success.

Use this scripting pattern to handle invalid streams automatically:

```sql
DECLARE
    removed_streams ARRAY DEFAULT ARRAY_CONSTRUCT();
    all_streams ARRAY DEFAULT PARSE_JSON('<STREAMS_JSON_ARRAY>');
    all_pks OBJECT DEFAULT PARSE_JSON('<STREAM_PKS_JSON_OBJECT>');
    result OBJECT;
    error_msg VARCHAR;
    bad_stream VARCHAR;
    max_retries INTEGER DEFAULT 50;
    attempt INTEGER DEFAULT 0;
    done BOOLEAN DEFAULT FALSE;
BEGIN
    WHILE (:done = FALSE AND :attempt < :max_retries) DO
        attempt := :attempt + 1;
        
        CALL <OMNATA_DATABASE>.API.CONFIGURE_OMNATA_INBOUND_SYNC(
            sync_slug => '<SYNC_SLUG>',
            sync_name => '<SYNC_NAME>',
            connection_slug => '<CONNECTION_SLUG>'::variant,
            sync_parameters => PARSE_JSON('{}'),
            sync_schedule => PARSE_JSON('{"mode":"manual","time_limit_mins":240,"warehouse":"<WAREHOUSE>"}'),
            stream_names => :all_streams,
            sync_strategy => '<SYNC_STRATEGY>'::variant,
            storage_behaviour => '<STORAGE_BEHAVIOUR>'::variant,
            sync_tuning_parameters => PARSE_JSON('{}'),
            inbound_storage_location => PARSE_JSON('{"normalized_column":"{{column_name}}","normalized_database":"<OMNATA_DATABASE>","normalized_object":"{{sync_slug}}_{{branch_name}}_{{stream_name}}","normalized_schema":"INBOUND_NORMALIZED","raw_database":"<OMNATA_DATABASE>","raw_object":"{{sync_slug}}_{{branch_name}}_{{stream_name}}","raw_schema":"INBOUND_RAW","raw_table_standard_change_tracking":false,"raw_table_type":"standard"}'),
            stream_primary_keys => :all_pks,
            sync_strategy_bulk_configuration => 'auto',
            storage_behaviour_bulk_configuration => '<STORAGE_BEHAVIOUR>'
        ) INTO :result;
        
        IF (:result:success::BOOLEAN = TRUE) THEN
            done := TRUE;
        ELSE
            error_msg := :result:error::VARCHAR;
            IF (error_msg LIKE 'Stream % not found by the plugin') THEN
                bad_stream := REPLACE(REPLACE(error_msg, 'Stream ', ''), ' not found by the plugin', '');
                removed_streams := ARRAY_APPEND(:removed_streams, :bad_stream);
                all_streams := ARRAY_EXCEPT(:all_streams, ARRAY_CONSTRUCT(:bad_stream));
                all_pks := OBJECT_DELETE(:all_pks, :bad_stream);
            ELSE
                RETURN OBJECT_CONSTRUCT(
                    'success', FALSE,
                    'attempts', :attempt,
                    'unexpected_error', error_msg,
                    'removed_streams', :removed_streams,
                    'remaining_stream_count', ARRAY_SIZE(:all_streams)
                )::VARCHAR;
            END IF;
        END IF;
    END WHILE;
    
    RETURN OBJECT_CONSTRUCT(
        'success', :done,
        'attempts', :attempt,
        'configured_stream_count', ARRAY_SIZE(:all_streams),
        'removed_streams', :removed_streams
    )::VARCHAR;
END;
```

### Placeholders to substitute

| Placeholder | Description |
|---|---|
| `<OMNATA_DATABASE>` | Omnata Sync Engine database name (appears 4 times in the CALL) |
| `<CONNECTION_SLUG>` | Connection slug from `DATA_VIEWS.CONNECTION` |
| `<SYNC_SLUG>` | User-chosen kebab-case identifier |
| `<SYNC_NAME>` | User-chosen human-readable name |
| `<WAREHOUSE>` | Warehouse for sync execution |
| `<SYNC_STRATEGY>` | `Incremental` or `Full Refresh` |
| `<STORAGE_BEHAVIOUR>` | `merge` or `append` |
| `<STREAMS_JSON_ARRAY>` | JSON array of lowercase stream names |
| `<STREAM_PKS_JSON_OBJECT>` | JSON object mapping each stream to its PK array |

### How the retry works

1. Attempts to create/update the sync with ALL streams
2. If a stream isn't found by the plugin, parses the error to get the stream name
3. Removes that stream from the array and PKs object
4. Retries -- converges in N+1 attempts where N is the number of invalid streams
5. Each attempt takes ~15 seconds (plugin validates against the live source)
6. Returns a JSON result with success status, configured count, and removed streams

### Key behaviours

- **Idempotent**: If the sync slug already exists, the proc updates it (adds/removes streams) rather than creating a duplicate
- **Stream validation**: The plugin calls the live source system to verify each stream exists -- streams must be real record types accessible via the connection
- **PK override**: The plugin's source-defined PK takes precedence over what you pass in `stream_primary_keys`
- **Bulk configuration defaults**: `sync_strategy_bulk_configuration => 'auto'` and `storage_behaviour_bulk_configuration` control what happens when new streams are auto-included in future

---

## Inbound Step 5: PK Reconciliation (Post-Creation)

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

Present the non-`["id"]` streams to the user for review. If any stream shows `["id"]` but
the user knows it should have a composite PK, they can reconfigure it in the Omnata UI.

---

## Inbound Step 6: Report Results

Present to the user:

1. **Success/failure** and number of attempts
2. **Configured stream count** vs. original count
3. **Removed streams** (not found by the plugin) -- these need to be added manually via the UI if they become available later, or the stream name may need correction
4. **Non-standard PKs** from the reconciliation query -- confirm these look right
5. **Next steps**: trigger the first run with `CALL <database>.API.RUN_SYNC(sync_slug => '<slug>')`

---

## Inbound Notes

- The `inbound_storage_location` uses Omnata template variables (`{{column_name}}`, `{{sync_slug}}`, `{{branch_name}}`, `{{stream_name}}`) -- these are NOT Snowflake or SQL variables, do not replace them
- The proc signature has 28 parameters but only 8 are required; the remaining use defaults
- Setting `"mode":"manual"` means the sync won't auto-schedule -- the user triggers runs manually or sets a schedule later via `SET_SYNC_SCHEDULE`
- The `sync_parameters` field is plugin-specific (e.g. NetSuite doesn't use any, but other plugins may require configuration here)

---

# Stopping Points

- After Outbound Step 1 if no existing syncs found (user must create one in UI first)
- After Outbound Step 1 if the user only needed to understand the existing config
- After Outbound Step 3 if the user wants to review the SQL before running
- After Jinja preview (Slack) if the user wants to adjust the message template
- After Outbound Step 5 for full confirmation
- After Inbound Step 4 if the user wants to review removed streams before continuing
- After Inbound Step 6 for full confirmation
