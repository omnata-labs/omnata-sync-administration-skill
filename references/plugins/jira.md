# Jira

| | |
|---|---|
| Plugin ID | `jira` |
| Plugin FQN | `OMNATA__JIRA` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: Yes |
| Docs | `apps/jira/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `jql_issues_clause` (optional): extra JQL filter for issues, for example `project = ABC`. No `order by` allowed.
- `issues_fields` (required, default `*all`): comma-separated issue fields to retrieve.

**Streams**: static list of 27 streams (the `issues` schema is built from the site's field list). Representative: `issues`, `issue_comments`, `issue_worklogs`, `issue_changelogs`, `projects`, `users`, `agile_sprints`, `asset_objects`. Child streams depend on a parent (`issue_*` on `issues`, `asset_object_types` on `asset_object_schemas`, `project_versions` on `projects`, `custom_field_contexts` on `fields`). All streams have a source-defined primary key. No stream sets an explicit `default_cursor_field`.

**Sync strategies supported**: `issues`, its child streams and `asset_objects` support `Incremental` and `Full Refresh`. Reference streams (`users`, `projects`, `statuses`, `priorities`, `fields`, `asset_object_schemas` and similar) are `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'jira-inbound',
    SYNC_NAME          => 'Jira to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['issues', 'issue_comments', 'projects', 'users'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
                            'issues_fields', '*all',
                            'jql_issues_clause', 'project = ABC'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Outbound

**Target types** (`OUTBOUND_TARGET_TYPE`):
- `Issues`: `Create`, `Upsert`
- `Service Desk Customers`: `Create`
- `Service Desk Organizations`: `Create`, `Upsert`
- `Asset Management Objects`: `Create`, `Upsert`
- `Asset Management Object Schemas`: `Create`, `Upsert`
- `Asset Management Object Types`: `Create`, `Upsert`

**Strategies** (`SYNC_STRATEGY_NAME`):
- `Create`: create new records.
- `Upsert`: create new records or update existing ones.

**Sync parameters** (`SYNC_PARAMETERS`): none for most target types. `Service Desk Organizations` requires `service_desk_ids` (multi-select of service desks).

**Field mappings** (`FIELD_MAPPINGS`): `field_mapping_selector`, with targets that depend on the target type. Required targets: Issues `summary`, `issuetype_name`, `project_key` (plus dynamic Jira fields). Service Desk Customers `display_name`, `email_address`. Service Desk Organizations `name`. Asset Management Objects `object_type_id`, `attributes`. Object Schemas `name`, `objectSchemaKey`. Object Types `name`, `iconId`, `objectSchemaId`.

**Required approach**: outbound syncs can only be created from the definition of an existing sync to this plugin. Copy `SYNC_PARAMETERS`, `FIELD_MAPPINGS` and the strategy from it (see Outbound Step 1 in `configure-syncs.md`) and adapt. Do not hand-build them from the fields listed above. If no sync to this plugin exists, the user must create one in the Omnata UI first.

## Notes

- OAuth connections need scopes per stream and target type (listed in the docs). Asset Management also needs `read:servicedesk-request` for workspace lookup.
- Issue child streams are fetched per issue, which adds significant time to initial syncs. Narrow with `jql_issues_clause` where possible.
- Consumer UDFs/UDTFs (all take `CONNECTION_PARAMETERS` first; work with API token, OAuth and Service Account OAuth connections): `FETCH_PROJECTS`, `FETCH_USERS`, `FETCH_GROUPS`, `FETCH_GROUP_MEMBERS(GROUP_ID, INCLUDE_INACTIVE_USERS)`, `FETCH_PROJECT_VERSIONS(PROJECT_KEY)`, `FETCH_ALL_ISSUE_FIELDS`, `JQL_QUERY(QUERY, RECORD_LIMIT, FIELDS)`, `JQL_QUERY_COUNT(QUERY)`, `CREATE_ISSUE`, `CREATE_OR_UPDATE_ORGANIZATION`, `DELETE_ISSUES(ISSUE_IDS_OR_KEYS)`.
- `DELETE_ISSUES` permanently deletes issues and their subtasks, one call per issue. Returns `ISSUE_ID_OR_KEY`, `STATUS` (`SUCCESS`, `NOT_FOUND`, `ERROR`), `RESULT`. Confirm with the user before running it.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/jira/README.md`
- Upsert matching key per target type was not traced in code. Copy from a UI-created sync.
- Manifest `docs_url` is the generic `https://docs.omnata.com`.
