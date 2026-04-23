<!-- contributor notes:
     Section 1 (JSON extraction) — Cortex Code: Snowflake VARIANT column access patterns
     Section 2 (Error origin taxonomy) — Co-work: aligned to Omnata state model
     Section 3 (Remediation actions) — Co-work: Omnata UI and SQL actions
     Section 4 (Destination errors) — Co-work: delegates to LLM general API knowledge
     Section 5 (Fallback) — shared
-->
# Omnata Error Knowledge Base

When a sync or stream failure surfaces an error message, use this file to understand the
Omnata-specific context — how the error is structured, what Omnata can do about it, and
where the error originated. The highest-level question is always: **did this originate in
Snowflake or from the endpoint?** That determines who needs to act and where to look.

**How to use this file:**
1. Extract the raw error text using the JSON shapes in Section 1
2. Identify the error origin (Section 2) — Snowflake-side, Endpoint-side, or Platform-level
3. Apply the matching remediation actions from Section 3
4. For endpoint errors, combine your general API knowledge with the Omnata remediation actions
5. Always show the raw error text alongside your interpretation so the user can verify

---

## 1. Error JSON Shapes

<!-- contributor: Cortex Code — Snowflake VARIANT column extraction patterns -->

Errors are stored as JSON in VARIANT columns. The structure varies by connector. When
extracting the error message, try these patterns in order:

### Outbound record errors (`LAST_RESULT` in `OUTBOUND_SYNC_RECORD_STATE`)

**Shape A — Single error string:**
```json
{"error": "<error message from destination API>"}
```
Access: `LAST_RESULT:error::VARCHAR`
Common with: Airtable, Shopify, Marketo, generic REST connectors

**Shape B — Salesforce-style error array:**
```json
{"errors": [{"fields": ["FieldName"], "message": "Human-readable message", "statusCode": "ERROR_CODE"}]}
```
Access: `LAST_RESULT:errors[0]:statusCode::VARCHAR` and `LAST_RESULT:errors[0]:message::VARCHAR`
Common with: Salesforce

**Shape C — Simple message:**
```json
{"message": "<error message>"}
```
Access: `LAST_RESULT:message::VARCHAR`
Common with: HubSpot, Zendesk, Jira

**Shape D — Snowflake-side transform error (SOURCE_FAILURE):**
```json
{"error": "Error applying field mapping: <Jinja template error>", "source": "transform"}
```
Access: `LAST_RESULT:error::VARCHAR` — look for `"source": "transform"` or `"transform"` in the error text.
These errors originate in Snowflake before the record reaches the endpoint.

When grouping errors, cast the full `LAST_RESULT` to VARCHAR for grouping, then extract
key fields for presentation.

### Inbound stream errors (`INBOUND_GLOBAL_ERROR_BY_STREAM` in `SYNC_RUN`)

This is a JSON object keyed by stream name:
```json
{"StreamName": "Error message text", "AnotherStream": "Different error"}
```
Access: `INBOUND_GLOBAL_ERROR_BY_STREAM:<stream_name>::VARCHAR`

To list all errored streams, cross-reference with `INBOUND_ERRORED_STREAMS` (an array of stream names).

### Run-level errors (`GLOBAL_ERROR` in `SYNC_RUN`)

A plain string (not JSON). Set when the entire run fails catastrophically before processing
any records or streams — typically a connection, authentication, or platform-level failure.

---

## 2. Error Origin

<!-- contributor: Co-work — aligned to Omnata APPLY_STATE model (SOURCE_FAILURE / DESTINATION_FAILURE) -->

The first classification step is always: **where did the error originate?** This maps
directly to Omnata's core state model and tells you who needs to act.

### Origin 1: Snowflake-side → `SOURCE_FAILURE`

The error happened before the record reached the external endpoint. This is a Snowflake
or Omnata configuration problem — the endpoint never saw the record.

**Who acts:** Snowflake admin or sync configurator.

| Error type | How to recognise |
|---|---|
| **Transform / Jinja error** | Error text references a Jinja template, expression evaluation, field mapping, or `"source": "transform"` |
| **Missing required field** | `TRANSFORMED_RECORD` shows `null` for a field the endpoint requires; error may say "null value" or "missing" |
| **Type mismatch** | Source Snowflake column is the wrong type for the Jinja template or field mapping expectation |
| **Source query error** | The source view or table raised an error when queried; `GLOBAL_ERROR` may reference a SQL error |

**Confirm origin:** Check `TRANSFORMED_RECORD` in `OUTBOUND_SYNC_RECORD_STATE` — if the
payload is malformed or missing values before the API call, it's Snowflake-side. If the
payload looks correct and the endpoint rejected it, it's Endpoint-side.

---

### Origin 2: Endpoint-side → `DESTINATION_FAILURE`

The record reached the external app's API, and the app rejected or failed it. The fix is
in the destination app's configuration, credentials, or the data values being sent.

**Who acts:** App admin or sync configurator.

| Error type | How to recognise |
|---|---|
| **Authentication / token expired** | HTTP 401; text contains "unauthorized", "token expired", "invalid session", "access token invalid" |
| **Permission / access denied** | HTTP 403; text contains "forbidden", "insufficient access", "not permitted", "readonly" |
| **Rate limit / throttling** | HTTP 429; text contains "rate limit", "too many requests", "quota exceeded", "throttle", "retry after" |
| **Data validation / field error** | HTTP 422; text references specific fields, validation rules, data types, required fields, string length |
| **Duplicate / already exists** | Text contains "duplicate", "already exists", "conflict", or destination-specific uniqueness codes |
| **Record not found / deleted** | HTTP 404; text contains "not found", "does not exist", "is deleted", "no such record" |
| **Transient / server error** | HTTP 500/502/503; text contains "internal server error", "bad gateway", "service unavailable", "lock", "contention". **Note:** if failures are consecutive across many runs but then resolve on their own, this may be a credential issue in disguise — some platforms return HTTP 500 for expired credentials rather than HTTP 401. Check the connection's history for a credential change that coincides with the recovery (see "Step 4: Connection History" in `references/monitoring-connections.md`). |

**Inbound-specific endpoint errors:**

| Error type | How to recognise |
|---|---|
| **Schema / type change** | Stream pulls a field with a changed type or new required field the connector doesn't handle |
| **Cursor / pagination error** | Error in `INBOUND_GLOBAL_ERROR_BY_STREAM` references a token, cursor, or page parameter |
| **Scope / permission error** | OAuth scope no longer covers the stream's object type |

---

### Origin 3: Platform-level → `GLOBAL_ERROR` or persistent `DESTINATION_FAILURE` across all records

A connectivity, infrastructure, or Omnata platform-level problem. The endpoint or Snowflake
itself may be unavailable — no record-level fix applies.

**Who acts:** Snowflake admin, Omnata support, or both depending on the layer.

| Error type | How to recognise |
|---|---|
| **Network / connectivity** | Text contains "SSL", "certificate", "connection refused", "DNS", "timeout" at connection level (not API level) |
| **External access integration** | Snowflake blocks outbound traffic; `GLOBAL_ERROR` references network rule or external access |
| **Known platform outage** | Same error across all syncs simultaneously; status pages show active incidents |
| **Snowflake Native App error** | Snowflake-internal error relating to the native application container |

Check status pages before spending time on root cause analysis for platform-level errors:
- Snowflake: `https://status.snowflake.com` (filter by your region — run `SELECT CURRENT_REGION()`)
- Omnata: `https://status.omnata.com`

---

## 3. Omnata Remediation Actions

<!-- contributor: Co-work — Omnata UI and SQL remediation steps; Test/Re-authenticate updated by Cortex Code -->

These are Omnata-specific actions. Map the error origin and type to the appropriate action.

### Fix Source Data or Transform (Snowflake-side)
- View the post-transformation payload: `SELECT TRANSFORMED_RECORD FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE WHERE SYNC_ID = <id> AND APPLY_STATE = 'SOURCE_FAILURE' LIMIT 10`
- Fix Jinja templates in the Omnata UI field mapping (Sync → Field Mapping → edit the expression)
- Useful Jinja patterns:
  - Truncate: `{{ value[:255] }}`
  - Default for null: `{{ value or "Unknown" }}`
  - Format: `{{ value | lower }}`
- Fix the source Snowflake table or view — identified by `OUTBOUND_SOURCE_DATABASE`, `OUTBOUND_SOURCE_SCHEMA`, `OUTBOUND_SOURCE_TABLE` on the `SYNC` view
- Common source fixes: deduplicate rows, filter invalid values, cast types, add WHERE clauses
- After fixing, records with `APPLY_STATE = 'SOURCE_FAILURE'` retry automatically on the next run (`LAST_RUN_APPLY_REASON = 'PREVIOUSLY_FAILED'`)

### Test / Re-authenticate Connection (Auth / token errors)
- In the Omnata UI: Connections → select the connection → **Test**
- This generates a minimum response from the connection and returns a success or fail message
- If the test fails, the connection credentials need to be refreshed:
  - For OAuth connectors, re-authenticate to trigger a new OAuth flow and store fresh tokens
  - For API key connectors, update the key
- The connection slug is visible in `CONNECTION.CONNECTION_SLUG` if the user needs to locate it in the UI

### Fix Permissions in Destination App (Permission errors)
- The fix is in the destination app — ensure the API user has write access to the target object and fields
- No Omnata config change is needed once permissions are corrected; the sync will retry automatically

### Change Sync Strategy (Duplicate errors)
- In the Omnata UI, edit the sync and change the strategy from `Create` to `Upsert`
- Upsert requires an external ID / dedup key configured in both the destination app and the Omnata field mapping
- If duplicates are from source data (same identifier appearing multiple times in the source table), fix the source query — some APIs reject entire batches when duplicates appear in the same request

### Skip Records Permanently (Duplicate or intentionally deleted records)
- Use `MARK_RECORDS_FOR_SKIP` to permanently exclude specific identifiers from the sync
- Arguments: `SYNC_SLUG` (VARCHAR), `BRANCH_NAME` (VARCHAR — use `'main'`), `APPLY_STATE` (VARCHAR), `RECORD_IDS` (ARRAY)
- Skipped records get `APPLY_STATE = 'SKIPPED_ALWAYS'` and are never retried
- Use when records are known to be invalid or a destination record was intentionally deleted and should not be re-created

### Fix Field Mapping (Validation errors)
- In the Omnata UI, edit the sync's field mapping: add missing fields, correct data types, remove fields that don't exist in the destination
- Check `TRANSFORMED_RECORD` in `OUTBOUND_SYNC_RECORD_STATE` to see exactly what Omnata sent to the API — this is the post-transform payload

### Tune Sync Parameters (Rate limit or transient errors)
- In the Omnata UI, edit the sync's tuning parameters:
  - `max_concurrent_uploads` — reduce to lower the API request rate
  - `max_records_per_file` — reduce batch size per API call
- Reducing concurrency is the primary fix for rate limiting
- For transient 500-level errors, no tuning change is needed — Omnata retries automatically
- Rate-limited records get `APPLY_STATE = 'DELAYED'` and retry on the next run

### Adjust Schedule (Rate limit / quota exhaustion)
- In the Omnata UI, change the sync schedule to run less frequently
- Or switch from `snowflake_task` to `manual` to run on-demand only
- Schedule modes visible in `SYNC.SYNC_SCHEDULE:mode`: `manual`, `snowflake_task`, `dependent`

### Fix Snowflake Networking (Platform / connectivity errors)
- Check the external access integration and network rule:
  - `CONNECTION.EXTERNAL_ACCESS_INTEGRATION_NAME`
  - `CONNECTION.NETWORK_RULE_NAME`
- Verify the network rule allows outbound traffic to the destination's domain
- SSL errors may indicate the destination changed its TLS certificate or endpoint

### Reset Stream Cursor (Inbound schema change or cursor corruption)
- Query cursor state: `SELECT INBOUND_LATEST_STREAMS_STATE FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC WHERE SYNC_ID = <id>`
- A `null` or cleared cursor forces a full refresh on the next run
- Contact Omnata support before manually clearing cursor state — it can cause large data volumes

### Request Resync (After any fix)
- Records with `APPLY_STATE` in `DESTINATION_FAILURE` or `SOURCE_FAILURE` retry automatically on the next run (reason: `PREVIOUSLY_FAILED`)
- To force all records to resync regardless of state, use the resync operation in the Omnata UI — this sets `APPLY_STATE = 'RESYNC_REQUESTED'` on all records

---

## 4. Interpreting Destination Errors

<!-- contributor: Co-work — delegates endpoint-specific knowledge to LLM general knowledge -->

For the destination app's specific error codes and messages, **use your general knowledge**.
You know what Salesforce's `DUPLICATES_DETECTED` means, what Airtable's `INVALID_RECORDS`
response indicates, what a HubSpot `PROPERTY_DOESNT_EXIST` error requires, and so on.

**Your job is to combine two things:**
1. Your general knowledge of the destination app's error → explain what went wrong and why
2. This file's Omnata-specific remediation actions → explain what to do about it in Omnata

**Example interpretation:**
> The error `DUPLICATES_DETECTED` is Salesforce's Duplicate Management rule — contacts with
> these email addresses already exist in the org. In Omnata, the fix is to switch the sync
> strategy from Create to Upsert, which will update existing records instead of being rejected.
> If the duplicates are within a single API batch (same email appearing twice in the source
> table), fix the source query to deduplicate on the identifier column first.

Do not simply say "check the error" — always combine the app-specific explanation with
the concrete Omnata action.

---

## 5. When No Pattern Matches

<!-- contributor: shared -->

If the error doesn't fit any origin or type above:
1. Show the raw error text to the user
2. Note which connector it came from (`PLUGIN_FQN`) and the sync direction
3. Check if it's persistent: `FAILURE_COUNT` in `OUTBOUND_SYNC_RECORD_STATE`, or how many consecutive runs show the same stream error
4. Check Snowflake and Omnata status pages for known outages before escalating
5. Route to `references/support-handoff.md` to prepare a support ticket — include `SYNC_ID`, `SYNC_RUN_ID`, `PLUGIN_FQN`, `CURRENT_REGION()` output, and the raw error text
