# <Plugin Name>

| | |
|---|---|
| Plugin FQN | `<DEVELOPER>__<PLUGIN_ID_UPPER>` |
| Page | `<plugin_id>.md` |

Look up directions, outbound strategies, target types, stream strategies and the docs link from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). This page holds only what the apps don't expose. Point the user to the plugin's `DOCS_URL` for explanations and vendor-side setup.

Writing rules for this page:
- Don't list outbound strategies, target types, stream catalogs or per-stream strategies. The apps return them.
- Keep the meaning of each sync parameter, gotchas, required approaches and warnings.
- Describe vendor-side setup in one or two lines and refer to the docs for the steps.
- Don't cite plugin source files or code internals.
- A tested, full `CONFIGURE_OMNATA_*` call for this plugin goes under `### Worked example` in its section. The Omnata docs don't publish these, so the plugin page is their home; `configure-syncs.md` stays generic.

## Connection

Follow `configure-connections.md`. Record only:
- **Methods**: the method names, and which fields are secrets.
- **Before you start**: anything the user must do in the vendor app (scopes, admin consent, sharing). Keep it short; the docs have the steps.
- **Quirks**: anything seen in testing (secret prefixes for redaction, `&` in endpoints, etc.).

## Inbound

Omit if the plugin has no inbound support.

**Sync parameters** (`SYNC_PARAMETERS`): each parameter's name, whether it's required, and what it does. If there are none, write "None, pass `OBJECT_CONSTRUCT()`."

**Streams**: one line on how they're discovered (static, dynamic, or driven by a sync parameter), plus anything the stream config doesn't make obvious, e.g. "Incremental doesn't mean delta fetching."

## Outbound

Omit if the plugin has no outbound support.

**Sync parameters** (`SYNC_PARAMETERS`): each parameter's name and what it does, so CoCo can adapt a copied definition.

**Field mappings**: `field_mapping_selector` or `jinja_template`, and any required mapping such as an identifier field.

**Before running**: a warning for any strategy that deletes, overwrites or sends messages to people.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

Gotchas that affect programmatic configuration only. Keep it short.
