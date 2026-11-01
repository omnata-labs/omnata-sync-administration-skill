# SFTP

| | |
|---|---|
| Plugin FQN | `OMNATA__SFTP` |
| Page | `sftp.md` |

Look up directions, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `SFTP Private Key only` (secret `ftp_private_key`) and `SFTP Password only` (secret `ftp_password`). Both also take `sftp_hostname`, `sftp_port` (default `22`), `ftp_username`, and optional `file_location` (base path on the server).
- **Before you start**: the private key must be an unencrypted RSA, Ed25519 or ECDSA key in OpenSSH or PEM format. Passphrase-protected keys are rejected ("Private key is passphrase protected, which is not supported").
- **Quirks**: only direct connectivity is supported. A wrong `file_location` fails with "Failed to change path on server".

## Inbound

Inbound reads CSV files.

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `multi_file` (Multi-File Individual, one stream per file, the default) or `multi_file_consolidated` (Multi-File Consolidated, all matching files into one `MultipleFiles` stream).
- `parent_folder_path` (required): folder to read.
- `filename_pattern` (optional): case-insensitive regex on file names. Blank includes every CSV file in the folder.
- `primary_key_columns` (optional, `multi_file` only): comma-separated columns that identify a row. Use the minimal identifying set; including changing value columns stores updates as duplicates. If blank, a primary key must still be chosen per stream.
- `header_row` (optional, default `1`): 1-indexed row holding column headers.

**Tuning parameters**: `ssh_transport_keepalive` (0 to 600 seconds, default 0 = off). Raise it if the SSH transport times out while rows load.

**Streams**: discovered from the files matching `parent_folder_path` and `filename_pattern`. No stream has a default cursor field.

## Notes

- Outbound: not supported.

## Sources

- Docs: `https://docs.omnata.com/omnata-product-documentation/omnata-sync-for-snowflake/apps/sftp`
- Not verified: whether `multi_file_consolidated` streams need `STREAM_PRIMARY_KEYS` set explicitly; parameter value types (string vs number) for `header_row`. Copy from a UI-created sync if unsure.
