# Mailgun

| | |
|---|---|
| Plugin FQN | `OMNATA__MAILGUN` |
| Page | `mailgun.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: one method, `API Key`. No OAuth.
- Fields: `api_key` (required, secret, the primary API key), `sending_key` (optional, secret, a domain sending key used for outbound sends instead of `api_key` if set), `region` (required, `us` or `eu`).

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `domains` (optional): comma-separated list of Mailgun domains to filter logs to. Omit it to get logs from all domains.

**Streams**: static, a single `logs` stream. Its primary key and cursor are source-defined, so you don't need to set them.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `domain` (required): the sending domain, chosen from the account's domains.

**Field mappings**: `field_mapping_selector`. `to` and `subject` are required. `from`, `text` and `html` are optional. If `from` is unmapped, it defaults to postmaster at the sending domain.

**Before running**: `Send` emails one message per new record through Mailgun. Record data, such as email addresses and message content, goes to Mailgun and to the recipients. Sent emails can't be recalled. Confirm the source table, recipients and content with the user, and wait for their explicit yes.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- The region sets the API host. A wrong region shows up when the connection is tested, not at sync time. Connections with no stored region fall back to `us`.
