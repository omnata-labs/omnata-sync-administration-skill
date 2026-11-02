# SFTP

| | |
|---|---|
| Plugin FQN | `OMNATA__SFTP` |
| Page | `sftp.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `SFTP Private Key only` (secret field `ftp_private_key`) and `SFTP Password only` (secret field `ftp_password`). Both also take `sftp_hostname`, `sftp_port` (default `22`), `ftp_username` and an optional base path `file_location`.
- **Before you start**: the key must be an unencrypted RSA, Ed25519 or ECDSA key in OpenSSH or PEM format. Passphrase-protected keys are rejected.
- **Quirks**: only direct connectivity is supported. A wrong `file_location` fails with "Failed to change path on server".

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `sync_mode` (required): `multi_file` (one stream per CSV file, the default) or `multi_file_consolidated` (all matching files into one stream).
- `parent_folder_path` (required): folder to read.
- `filename_pattern` (optional): case-insensitive regex on file names. Blank includes every CSV file in the folder.
- `primary_key_columns` (optional, `multi_file` only): comma-separated columns that identify a row. Use the minimal identifying set; including changing value columns stores updates as duplicates.
- `header_row` (optional, default `1`): 1-indexed row holding column headers.
- `ssh_transport_keepalive` (tuning, 0 to 600 seconds, default 0 = off): raise it if the SSH transport times out while rows load.

**Streams**: discovered from the CSV files matching `parent_folder_path` and `filename_pattern`, so the list changes as files are added.

## Notes

- Whether `multi_file_consolidated` needs `STREAM_PRIMARY_KEYS` set wasn't verified, nor whether `header_row` is passed as a string or number. Copy from a UI-created sync if unsure.
