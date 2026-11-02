# Hubspot

| | |
|---|---|
| Plugin FQN | `OMNATA__HUBSPOT` |
| Page | `hubspot.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Connection

Follow `configure-connections.md`.
- **Methods**: `Private App` (secret `access_token`, the private app access token) and `Service Key` (secret `access_token`, the HubSpot service key). Both store the token under the same secret name.
- **Before you start**: the token needs scopes for the objects being synced. A 403 error includes HubSpot's response, which names the missing scope.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`):
- `include_associations` (required checkbox): fetch associations with each record. Expensive on incremental runs, because changed objects are fetched one by one.
- `check_archive` (required checkbox): fetch archived objects and mark them deleted. Adds API calls.
- `include_form_submissions` (required checkbox): adds one form submissions stream per HubSpot form.
- `associations_warning` is read-only. Don't pass it.

**Streams**: static CRM objects (for example `contacts`, `companies`, `deals`), plus custom objects discovered from the account schema. Form submission streams appear only when `include_form_submissions` is true. Archived records are handled within the main streams via `check_archive`, not separate streams.

## Outbound

**Sync parameters** (`SYNC_PARAMETERS`): none are required.
- Object Records target: `hubspot_object` (target object), `hubspot_id_field` (record ID or a unique property such as email), `marketable_contact` (marketing status for imported contacts), `cleanup_default_associations` (remove default associations HubSpot adds after labelled association removal), `clear_null_field_values` (default false, clears nulls with an extra API pass).
- Association Delete target: `from_object_type`, `to_object_type`.

**Field mappings**: `field_mapping_selector`. Object Records targets come from the properties of `hubspot_object`; association targets take OBJECT columns. Association Delete requires `from_id` and `to_id`.

**Before running**: `Delete` removes associations between records. This can't be undone. Show the user what will be affected and wait for their explicit yes; don't treat an unclear reply as confirmation. `clear_null_field_values` overwrites existing HubSpot values with blanks when the source is null; confirm it with the user too.

Outbound syncs are created by copying an existing sync to this plugin (Outbound Step 1 in `configure-syncs.md`). If none exists, the user creates one in the Omnata UI first.

## Notes

- Outbound uses HubSpot import jobs, so the private app needs the `crm.import` scope. Dates are formatted MM/DD/YYYY.
- HubSpot doesn't bump last-modified dates on association changes, so incremental syncs with `include_associations` can miss association-only changes.
- Consumer UDTF `SINGLE_SEND_EMAIL(CONNECTION_PARAMETERS, EMAIL_ID, TO_ADDRESS)` sends an existing marketing email to one recipient and returns `EMAIL_ID`, `STATUS` (`SUCCESS` or `ERROR`) and `RESPONSE`. Needs Marketing Hub Enterprise or the transactional email add-on.
- **Before running** `SINGLE_SEND_EMAIL`: it sends a real email and creates the recipient as a HubSpot contact if missing. Show the user the email ID and recipients, and confirm with the user before using it.
- Whether checkbox values are stored as booleans or strings wasn't verified. Copy from a UI-created sync if unsure.
