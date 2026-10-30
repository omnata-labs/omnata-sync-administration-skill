# Jira

| | |
|---|---|
| Plugin FQN | `OMNATA__JIRA` |
| Page | `jira.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`. OAuth connections need scopes per stream and target type (see the docs). Asset Management also needs `read:servicedesk-request` for workspace lookup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `jql_issues_clause` (optional): extra JQL filter for issues, for example project = ABC. No order by allowed.
- `issues_fields` (required, default `*all`): comma-separated issue fields to retrieve.

**Streams**: static list, for example `issues`, `issue_comments`, `projects`. Issue child streams depend on `issues`. The `issues` schema is built from the site's field list.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`): none for most target types. `Service Desk Organizations` requires `service_desk_ids` (multi-select of service desks).

**Field mappings**: `field_mapping_selector`. Targets depend on the target type. Required targets:
- Issues: `summary`, `issuetype_name`, `project_key`.
- Service Desk Customers: `display_name`, `email_address`.
- Service Desk Organizations: `name`.
- Asset Management Objects: `object_type_id`, `attributes`.
- Asset Management Object Schemas: `name`, `objectSchemaKey`.
- Asset Management Object Types: `name`, `iconId`, `objectSchemaId`.

**Before running**: outbound syncs create and change issues in Jira. Confirm with the user before running.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Issue child streams are fetched per issue, which slows initial syncs. Narrow with `jql_issues_clause` where possible.
- Consumer UDFs/UDTFs all take `CONNECTION_PARAMETERS` first and work with API token, OAuth and Service Account OAuth connections: `FETCH_PROJECTS`, `FETCH_USERS`, `FETCH_GROUPS`, `FETCH_GROUP_MEMBERS(GROUP_ID, INCLUDE_INACTIVE_USERS)`, `FETCH_PROJECT_VERSIONS(PROJECT_KEY)`, `FETCH_ALL_ISSUE_FIELDS`, `JQL_QUERY(QUERY, RECORD_LIMIT, FIELDS)`, `JQL_QUERY_COUNT(QUERY)`, `CREATE_ISSUE`, `CREATE_OR_UPDATE_ORGANIZATION`, `DELETE_ISSUES(ISSUE_IDS_OR_KEYS)`.
- **Before running** `DELETE_ISSUES`: it permanently deletes issues and their subtasks, one call per issue. Show the user the issue keys and count. Confirm with the user before using it. It returns `ISSUE_ID_OR_KEY`, `STATUS` (`SUCCESS`, `NOT_FOUND` or `ERROR`) and `RESULT`.
- The Upsert matching key per target type wasn't verified. Copy from a UI-created sync.
