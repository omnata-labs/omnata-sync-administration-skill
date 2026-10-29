# Microsoft Entra ID

| | |
|---|---|
| Plugin ID | `entra_id` |
| Plugin FQN | `DATA_ENGINEERS__ENTRA_ID` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/entra_id/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `max_concurrent_streams` (required): slider from 1 to 10, default 5. Maximum number of streams processed concurrently.

**Streams**: static list: `users`, `user_identities`, `user_assigned_licenses`, `user_assigned_plans`, `user_provisioned_plans`, `user_license_assignment_states`, `groups`, `user_group_memberships`. Every stream has a source-defined primary key (several are composite, for example `userId` + `skuId`) and a source-defined cursor, with no default cursor field. No overrides via `STREAM_PRIMARY_KEYS` / `STREAM_CURSOR_FIELDS` should be needed.

**Sync strategies supported**: `Full Refresh` only, for every stream.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'entra_id-inbound',
    SYNC_NAME          => 'Microsoft Entra ID to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['users', 'groups', 'user_group_memberships'],
    SYNC_STRATEGY      => 'Full Refresh'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('max_concurrent_streams', 5),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- The connection's Entra app registration needs Microsoft Graph application permissions: `User.Read.All` (user streams), `Group.Read.All` (`groups`), `GroupMember.Read.All` (`user_group_memberships`). Missing permissions cause failures on the corresponding streams.
- Every run re-pulls the full directory. Docs recommend historising downstream (SCD Type 2) if change history matters.
- `max_concurrent_streams` is the main tuning lever for Graph API throttling.

## Sources

- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/entra_id/README.md`
- `inbound_stream_list` sets `primary_key_can_be_composite=False` while several streams declare composite keys. Behavioural impact not verified.
- Manifest `docs_url` points to `apps/microsoft-entra-id`, but the docs folder is `entra_id`.
- The FQN is derived from `developer_id='data_engineers'` (developer name is Monitorial Ltd). Not verified against a live `PLUGIN_FQN` value.
