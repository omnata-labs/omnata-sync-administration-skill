# Aerobotics

| | |
|---|---|
| Plugin FQN | `MONITORIAL__AEROBOTICS` |
| Page | `aerobotics.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: static list (e.g. `farms`, `orchards`, `surveys`). Some streams depend on a parent stream, so select parents alongside children.

## Notes

- The access token only works with the Aerobotics Enterprise API add-on.
- Insurance module streams mentioned in the docs aren't in the plugin's stream list.
- The developer is Monitorial, so the FQN prefix is `MONITORIAL`, not `OMNATA`.
