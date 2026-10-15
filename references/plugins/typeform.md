# Typeform

| | |
|---|---|
| Plugin ID | `typeform` |
| Plugin FQN | `OMNATA__TYPEFORM` (as shown in `DATA_VIEWS.CONNECTION.PLUGIN_FQN`) |
| Directions | Inbound: Yes. Outbound: No |
| Docs | `apps/typeform/README.md` |

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `workspace` (required, dynamic dropdown): the Typeform workspace whose forms become streams. One workspace per sync.

**Streams**: dynamic, depend on `workspace`. Three streams per form, named from the form title: `<Form Title> - Responses` (key `response_id`), `<Form Title> - Answers` (key `answer_id`), `<Form Title> - Fields` (key `id`). Up to 200 forms are listed. All streams define a primary key and source-defined cursor.

**Sync strategies supported**: Responses and Answers support `Incremental` and `Full Refresh`. Fields is `Full Refresh` only.

```sql
CALL OMNATA_SYNC_ENGINE.API.CONFIGURE_OMNATA_INBOUND_SYNC(
    SYNC_SLUG          => 'typeform-inbound',
    SYNC_NAME          => 'Typeform to Snowflake',
    CONNECTION_SLUG    => '<connection_slug>'::VARIANT,
    STREAM_NAMES       => ['<Form Title> - Responses', '<Form Title> - Answers'],
    SYNC_STRATEGY      => 'Auto'::VARIANT,
    STORAGE_BEHAVIOUR  => 'merge'::VARIANT,
    SYNC_PARAMETERS    => OBJECT_CONSTRUCT('workspace', '<workspace_id>'),
    SYNC_SCHEDULE      => OBJECT_CONSTRUCT('mode', 'manual', 'warehouse', '<warehouse>', 'time_limit_mins', 60),
    RAISE_ERRORS       => true
);
```

## Notes

- Stream names contain the form title verbatim, so renaming a form in Typeform changes the stream name.
- `workspace` is a dynamic dropdown; copy its stored shape from a UI-created sync if a bare ID string is not accepted.
- Connection has a `data_center` parameter that sets the API host.

## Sources

- Code: `omnata-labs/plugin-typeform` at `src/plugin.py`
- Docs: `omnata-docs-gitbook/omnata-sync-for-snowflake/apps/typeform/README.md` (agrees: no outbound, Full Refresh and Incremental)
- Not verified: the exact stored value format for `workspace` (ID vs object with metadata).
