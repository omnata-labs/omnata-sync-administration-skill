# Microsoft Dynamics 365 Business Central

| | |
|---|---|
| Plugin ID | `dynamics_365_business_central` |
| Plugin FQN | `MONITORIAL__DYNAMICS_365_BUSINESS_CENTRAL` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/microsoft-dynamics-365-business-central/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `companies` (required, multi-select): list of Business Central company IDs to retrieve data for. Options come from the `/companies` endpoint (value is the company `id`).
- `api_set` (required, default `api`): which API set to read. Values: `api` (v2.0 API), `ODataV4`, `custom` (Custom API, uses the custom API publisher/group/version from the connection).

**Streams**: Dynamic. The stream list is built from the `$metadata` document of the selected `api_set`, so changing `api_set` changes the stream list entirely. Stream names come from the entity set names, plus generated child streams for collection navigation properties (for example `<parent>_<child>` line item streams, which depend on their parent stream). Every stream has a source-defined primary key (entity keys plus `companyId` for non-company entities). Streams without a `lastModifiedDateTime` / `systemModifiedAt` style field (or a posting date field for ODataV4) have no default cursor.

**Sync strategies supported**: Streams with a detected cursor field support `Incremental` and `Full Refresh`. Streams without one support `Full Refresh` only. Generated child (expansion) streams support `Incremental` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'dynamics_365_business_central-inbound',
    SYNC_NAME          => 'Microsoft Dynamics 365 Business Central to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['companies', 'accounts', 'currencies'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT(
        'companies', ARRAY_CONSTRUCT('<company_id>'),
        'api_set', 'api'
    ),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- `companies` values are GUIDs, not display names. Look them up from an existing UI-created sync or the Business Central `/companies` API.
- Access tokens last 60 minutes. Long-running syncs should use a connection on the "OAuth (Plugin managed tokens)" method.
- Docs recommend grouping objects into several dedicated syncs for large initial loads, and using `Full Refresh` for entities where deletes matter (for example accounts, companies, currencies, employees), since deletes cannot be captured incrementally.
- Docs list unsupported endpoints: timeRegistrationEntries, subscriptions, picture, documentAttachment, pdfDocument.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/microsoft-dynamics-365-business-central/README.md`. Folders `dynamics_365_business_central` and `dynamics_business_central` contain only `release-history.md`.
- Stream names in the example are taken from the docs entity list; actual names are generated from tenant metadata and could not be verified from code. Exact value format for a multi-select dropdown parameter (array of IDs) is assumed.
