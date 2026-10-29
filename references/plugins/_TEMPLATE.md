# <Plugin Name>

| | |
|---|---|
| Plugin ID | `<plugin_id>` |
| Plugin FQN | `<DEVELOPER>__<PLUGIN_ID_UPPER>` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes/No. Outbound: Yes/No |
| Docs | `apps/<docs_folder>/README.md` |

## Connection

Follow `configure-connections.md`. Record only what's specific to this plugin:
- **Methods**: each method from `CONNECTION_FORM()`, its fields (mark secret ones), and whether it uses OAuth (grant type, client auth method).
- **Where to get it**: per method, direct console links, APIs or scopes to enable, and common blockers.
- **App-side access**: anything the user must do in the app for syncs to see data (sharing, permissions, admin consent).
- **Credentials call**: an `UPDATE_CONNECTION_OBJECTS` example with placeholders, and the OAuth values from the plugin's template if any. Put a line before it recommending the Omnata UI route for secrets, and saying the SQL records the value in query history.
- **Quirks**: secret prefixes for redaction, `&` in endpoints (needs `--enable-templating STANDARD`), anything else seen in testing.

## Inbound

Omit this section entirely if the plugin does not support inbound.

**Sync parameters** (`SYNC_PARAMETERS`): list each inbound sync parameter with name, whether required, and what it does. If there are none, write "None, pass `OBJECT_CONSTRUCT()`."

**Streams**: how streams are discovered (static list, dynamic from the API, depends on a sync parameter). Name a few representative streams. Note any streams without a source-defined primary key or default cursor (these need `STREAM_PRIMARY_KEYS` / `STREAM_CURSOR_FIELDS`).

**Sync strategies supported**: which of `Incremental` / `Full Refresh` streams support, in general terms.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => '<plugin_id>-inbound',
    SYNC_NAME          => '<Plugin Name> to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => [<representative streams>],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(<params or empty>),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

Omit this section entirely if the plugin does not support outbound.

**Target types** (`OUTBOUND_TARGET_TYPE`): list each `outbound_target_types` label and the strategies it supports. If the plugin defines none, write "Not used."

**Strategies** (`SYNC_STRATEGY_NAME`): list each strategy name exactly as the plugin registers it, with one line on behaviour.

**Sync parameters** (`SYNC_PARAMETERS`): list each outbound sync parameter with name, whether required, and what it does.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector` or `jinja_template`, and what the target fields are (static list, dynamic from the API object chosen in sync parameters, etc.). Note any required mappings such as an identifier field for Update/Upsert.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

Plugin-specific caveats that affect programmatic configuration only (API limits that dictate tuning, prerequisites on the connection, parameters that change the stream list, etc.). Keep it short.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/<docs_folder>/README.md`
- Conflict: where the docs and the plugin's behaviour disagree, say what the docs claim and what this page follows.
- Anything you could not verify, say so here.
- Do not cite plugin source files, line numbers or code internals ("in code", "stub", "commented out", form names). Consumers cannot open them; describe behaviour only, and put code citations in the PR body.
