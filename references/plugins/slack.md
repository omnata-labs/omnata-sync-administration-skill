# Slack

| | |
|---|---|
| Plugin FQN | `OMNATA__SLACK` |
| Page | `slack.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- OAuth scopes requested: `chat:write`, `users:read.email`, `users:read`, `channels:read`.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `start_date` (optional): labelled "Start Date". No effect was verified, so leave it unset.

**Streams**: a single static stream, `conversations_list`.

## Outbound

> **Warning: third-party sharing.** Outbound syncs post Snowflake row data, including any personal data in the mapped columns, to Slack channels where members can read it. Messages can't be unsent by Omnata. Tell the user this, and confirm the channel and columns, before configuring an outbound sync.

**Sync parameters** (`SYNC_PARAMETERS`):
- `channel` (required): the channel to post in. The bot user must be invited to the channel for it to appear. The stored value includes channel metadata (shape below). Get the channel ID and name from an existing Slack sync's `SYNC_PARAMETERS`.

**Field mappings**: `jinja_template` (labelled "Message Template"). The template references source columns as `row['COLUMN_NAME']`.

**Before running**: `Post Message` posts a message built from row data into the Slack channel on record create, where every channel member can read it. Confirm the channel and message template with the user before using it.

### Worked example

Channel parameter shape:

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

Message template mapping. Preview it first ("Jinja template preview" in `configure-syncs.md`):


```sql
OBJECT_CONSTRUCT(
    'mapper_type', 'jinja_template',
    'jinja_template', '{{ row[''FIRST_NAME''] }} {{ row[''LAST_NAME''] }} ({{ row[''EMAIL''] }}) from {{ row[''ORGANIZATION''] }}.\nInstalled {{ row[''PRODUCT_NAME''] }} in {{ row[''ACCOUNT''] }} ({{ row[''REGION''] }}).',
    'additional_column_expressions', OBJECT_CONSTRUCT()
)
```

Full call, with positional parameters in signature order:

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

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- `Post Message` acts only on new records. Updated, deleted and unchanged records post nothing.

