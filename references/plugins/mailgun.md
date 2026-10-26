# Mailgun

| | |
|---|---|
| Plugin ID | `mailgun` |
| Plugin FQN | `OMNATA__MAILGUN` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/mailgun/README.md` |

## Connection

Follow `configure-connections.md`.
- **Methods**: one method, `API Key`. Fields: `api_key` (required, secret, primary API key), `sending_key` (optional, secret, domain sending key; used for outbound sends instead of `api_key` if set), `region` (required dropdown, `us` or `eu`; selects `api.mailgun.net` or `api.eu.mailgun.net`). No OAuth.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `domains` (optional): comma-separated list of Mailgun domains to filter logs to, e.g. `'sandbox123.mailgun.org, example.com'`. Omit for logs from all domains.

**Streams**: static, a single stream `logs`. It has source-defined primary key `id` and default cursor `@timestamp`, so no `STREAM_PRIMARY_KEYS` / `STREAM_CURSOR_FIELDS` are needed.

**Sync strategies supported**: `logs` supports both Incremental and Full Refresh.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'mailgun-inbound',
    SYNC_NAME          => 'Mailgun to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['logs'],
    SYNC_STRATEGY      => 'Incremental'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(),  -- optionally OBJECT_CONSTRUCT('domains', '<domain1>,<domain2>')
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`): Not used.

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Send`: sends one email per new record via the Mailgun Messages API.

**Sync parameters** (`SYNC_PARAMETERS`):
- `domain` (required, dynamic dropdown of the account's domains): sending domain.

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector` over a static list: `to` (required), `subject` (required), `from`, `text`, `html`. If `from` is unmapped it defaults to `postmaster@<domain>`.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- The region determines the API host, so a wrong region surfaces at connection time (the connection test lists domains), not sync time. Connections without a stored `region` fall back to `us`.
- Outbound sends are processed with concurrency 2, batch size 10.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/mailgun/README.md` (not re-checked for outbound in this update; previously said inbound only).
- Not verified: whether whitespace in `domains` matters (code strips each entry, so it should not).
