# BambooHR

| | |
|---|---|
| Plugin FQN | `MONITORIAL__BAMBOOHR` |
| Page | `bamboohr.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: dynamic. `company_information` and `employees` are always present. One stream per employee-related table is generated from the account's metadata, so the list varies by account.

## Notes

- The API key user's BambooHR permissions decide which fields and employees are visible.
- Table stream names come from the account's metadata, so list streams before hard-coding names.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
