# Typeform

| | |
|---|---|
| Plugin FQN | `OMNATA__TYPEFORM` |
| Page | `typeform.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

- The connection has a `data_center` parameter that sets the API host.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `workspace` (required): the Typeform workspace whose forms become streams. One workspace per sync.

**Streams**: dynamic, driven by `workspace`. Each form gives three streams named from the form title, e.g. `<Form Title> - Responses`, plus Answers and Fields streams. Up to 200 forms are listed.

## Notes

- Stream names contain the form title verbatim, so renaming a form in Typeform changes the stream name.
- `workspace` is a dynamic dropdown. Copy its stored shape from a UI-created sync if a bare ID string isn't accepted.
