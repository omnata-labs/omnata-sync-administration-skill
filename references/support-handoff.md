<!-- owner: co-work — do not edit if you are not Claude Co-work. -->
---
name: omnata-support-handoff
description: "Advise the user on what was found during sync diagnosis, then offer to create an Omnata support ticket. Use when: diagnosis is complete and the user needs help deciding next steps, the error could not be resolved through self-service, the user asks to contact Omnata support, or the user asks to raise a ticket. Triggers: contact support, raise a ticket, submit a ticket, Omnata support, support ticket, report a bug, who do I contact, can Omnata help."
---

# Omnata Support Handoff

After diagnosing a sync failure, advise the user on what was found and offer to prepare
a support ticket for Omnata if the issue requires their involvement.

## When to use this reference

Use this after one or more diagnostic steps from the monitoring or event table workflows
have run. It is the terminal step in the diagnostic chain — it should not be the first
step unless the user has explicitly asked to contact support.

Also use this when the user directly asks to raise a support ticket, even if diagnosis
has not yet been completed — in that case, run the appropriate diagnostic workflow first
to gather the context needed for the ticket.

## Prerequisites

- Web access to fetch status pages (required for Step 1)
- At least one of the following gathered from prior diagnostic steps:
  - SYNC_ID and SYNC_NAME
  - SYNC_RUN_ID (from a failing run)
  - Error text from GLOBAL_ERROR, LAST_RESULT, or INBOUND_GLOBAL_ERROR_BY_STREAM
  - Error origin classification from `references/error-knowledge-base.md`

---

## Workflow

### Step 1: Check Status Pages for Known Incidents

**Goal:** Before advising the user, determine whether a known platform incident —
on either Omnata's side or Snowflake's side — already explains the failure. Run
both checks before drawing conclusions.

#### Step 1a: Get the User's Snowflake Region

Omnata Sync Engine is a Snowflake Native Application. Snowflake outages are regional,
so always identify the user's region before checking the Snowflake status page.

**Execute:**

```sql
SELECT CURRENT_REGION() AS SNOWFLAKE_REGION
```

This returns a value like `AWS_US_EAST_1`, `AZURE_EASTUS2`, or `GCP_EUROPE_WEST4`.
Keep this value — it is used to filter the Snowflake status page in Step 1b.

#### Step 1b: Check the Snowflake Status Page

**Fetch:**

```
GET https://status.snowflake.com/api/v2/incidents.json
```

Parse the response for active incidents (status not `resolved`):

```
incidents[*] where status IN ["investigating", "identified", "monitoring"]
```

For each active incident, check the affected `components[*].name` for two things:
1. Whether the component name includes the user's region (e.g. `AWS US East 1`)
2. Whether the component name includes `Native Apps` or `Snowpark Container Services`
   (the runtime Omnata uses)

**Region name mapping** — Snowflake's status page uses human-readable region names.
Map `CURRENT_REGION()` output to the status page format:

| CURRENT_REGION() value | Status page region label |
|---|---|
| `AWS_US_EAST_1` | `AWS US East 1` |
| `AWS_US_EAST_2` | `AWS US East 2` |
| `AWS_US_WEST_2` | `AWS US West 2` |
| `AWS_EU_WEST_1` | `AWS EU West 1` |
| `AWS_EU_WEST_2` | `AWS EU West 2` |
| `AWS_AP_SOUTHEAST_1` | `AWS AP Southeast 1` |
| `AWS_AP_SOUTHEAST_2` | `AWS AP Southeast 2` |
| `AZURE_EASTUS2` | `Azure East US 2` |
| `AZURE_WESTEUROPE` | `Azure West Europe` |
| `GCP_US_CENTRAL1` | `GCP US Central 1` |
| `GCP_EUROPE_WEST4` | `GCP Europe West 4` |

If the user's region does not appear in this table, use partial string matching on the
region identifier to find the closest component name on the status page.

**If an active Snowflake incident affects Native Apps in the user's region:**
- Tell the user: there is a known Snowflake platform incident in their region that
  may be causing the Omnata sync failure
- Share the incident name, affected components, and latest update
- Provide the Snowflake status page URL: https://status.snowflake.com/
- Note: submitting an Omnata support ticket will not resolve a Snowflake-side incident,
  but include it in the ticket context if one is raised anyway

#### Step 1c: Check Omnata Status for Known Incidents

**Fetch:**

```
GET https://status.omnata.com/api/v2/incidents.json
```

Parse the response for active incidents (status not `resolved`):

```
incidents[*] where status IN ["investigating", "identified", "monitoring"]
```

For each active incident, check whether it affects the Omnata Sync Engine component
by looking at `incident_updates` body text or `components[*].name`.

**If an active Omnata incident is found:**
- Tell the user: there is a known Omnata incident currently in progress
- Share the incident name, current status, and the latest update message
- Provide the status page URL: https://status.omnata.com/
- Advise them to monitor the status page — a support ticket is unlikely to accelerate
  resolution for a platform-wide incident
- Stop here unless the user explicitly wants to submit a ticket anyway

#### Step 1 Summary

Present a two-line status summary before continuing:

```
Snowflake ([region]): [All systems operational / Active incident: <name>]
Omnata:               [All systems operational / Active incident: <name>]
```

If either platform has an active incident in the user's region, note it prominently
in any support ticket raised in later steps.

**If both are clear:** Continue to Step 2.

---

### Step 2: Present the Advisory Summary

**Goal:** Give the user a clear, non-technical summary of what was found and what their
options are.

Present the following in plain language:

**What happened:**
- Which sync failed (name and direction: inbound/outbound)
- When it last ran and what its current health state is
- The error in plain English (not just the raw code — explain what it means)

**Error classification:**
- State the error origin from `references/error-knowledge-base.md`
- Explain whether this is a data/config issue (user-fixable) or a platform/connectivity
  issue (may need Omnata)

**What the user can try:**
- List the applicable self-service remediation actions from the error KB
- Be specific: "In the Omnata UI, go to Connections → [connection name] → Edit → Re-authenticate"
  not "try re-authenticating"

**Whether a support ticket is recommended:**

Always offer the option to raise a ticket — never block or discourage it. A customer
may need Omnata's help to understand or apply a self-service step, even when the root
cause is a configuration or data issue.

Present the self-service steps first, then close with the ticket offer framed by one
of these two positions:

**Likely to need Omnata support** — lead with the offer:
> "This looks like it may need Omnata's involvement. Would you like me to prepare
> a support ticket?"

Use this framing when ANY of the following are true:
- The error did not match any known origin or type (Section 5 fallback in the error KB)
- The event table stack trace points to Omnata platform code (not connector or user config)
- The error is a transient/server error (Origin 2 — HTTP 500/502/503) but has persisted across 5+ runs with no recovery
- The error is a platform-level network/connectivity error (Origin 3) and Snowflake networking appears correct
- FAILURE_COUNT is very high (50+) and the cause is still unclear

**Likely self-serviceable** — offer the ticket as a follow-up option:
> "The steps above should resolve this. If you'd like Omnata's help walking through
> them, I can prepare a support ticket — just say the word."

Use this framing for errors where a clear remediation exists (duplicates, auth expiry,
permission gaps, rate limits, field validation, deleted records). The user may still
want assistance and should never be told a ticket is unnecessary.

---

### Step 3: Assemble the Ticket Payload

**Goal:** Build a complete, self-contained ticket from all diagnostic data gathered during
the session.

Collect the following fields. Use `null` or `not available` if a field was not gathered
during diagnosis.

```
TICKET CONTEXT — gather before drafting

Sync details (from DATA_VIEWS.SYNC):
  - SYNC_NAME
  - SYNC_ID
  - SYNC_SLUG
  - SYNC_DIRECTION (inbound / outbound)
  - PLUGIN_FQN
  - HEALTH_STATE
  - LATEST_RUN_START

Run details (from DATA_VIEWS.SYNC_RUN):
  - SYNC_RUN_ID
  - RUN_START_DATETIME
  - RUN_END_DATETIME
  - GLOBAL_ERROR (if set)
  - INBOUND_ERRORED_STREAMS (if inbound)

Record details (from DATA_VIEWS.OUTBOUND_SYNC_RECORD_STATE, if outbound):
  - FAILURE_COUNT (max across failing records)
  - Sample LAST_RESULT error text (top 1-2 distinct error patterns)
  - APPLY_STATE distribution

Event table details (if event-table-diagnostics was run):
  - snow.patch (Omnata app version — from RESOURCE_ATTRIBUTES)
  - snow.warehouse.name
  - EXCEPTION_TYPE
  - EXCEPTION_MESSAGE
  - STACKTRACE (last 3-5 frames only — truncate for readability)
  - Lifecycle phase where run stopped (last SPAN_EVENT before failure)

Error classification:
  - Error origin and type (from error-knowledge-base.md)
  - Self-service steps already attempted (if any)
```

---

### Step 4: Draft the Support Communication

**Goal:** Format the ticket as either an email or a portal submission.

#### Option A — Email

**Subject line format:**
```
[Company Name] — [Connector] sync failure: [short description]
```

Examples:
```
Acme Corp — Salesforce sync failure: GLOBAL_ERROR on run 2847
Acme Corp — Airtable sync failure: 24,940 records with DESTINATION_FAILURE
```

**Email body:**

```
To: support@omnata.com

Subject: [formatted subject above]

Hi Omnata Support,

We're experiencing a failure with one of our Omnata Sync Engine syncs and would
appreciate your assistance.

── SYNC DETAILS ──────────────────────────────────────────────
Sync Name:        [SYNC_NAME]
Sync ID:          [SYNC_ID]
Sync Slug:        [SYNC_SLUG]
Direction:        [SYNC_DIRECTION]
Connector:        [PLUGIN_FQN]
Health State:     [HEALTH_STATE]
Last Run Start:   [LATEST_RUN_START]

── FAILING RUN ───────────────────────────────────────────────
Sync Run ID:      [SYNC_RUN_ID]
Run Start:        [RUN_START_DATETIME]
Run End:          [RUN_END_DATETIME]

── ERROR DETAILS ─────────────────────────────────────────────
[If GLOBAL_ERROR is set:]
Global Error:
  [GLOBAL_ERROR text]

[If outbound record failures:]
Apply State:      DESTINATION_FAILURE
Failure Count:    [MAX FAILURE_COUNT] (max across failing records)
Sample Error:
  [LAST_RESULT text — top error pattern]

[If inbound stream failures:]
Errored Streams:  [INBOUND_ERRORED_STREAMS]
Stream Errors:
  [INBOUND_GLOBAL_ERROR_BY_STREAM — key: value per stream]

── EVENT TABLE DIAGNOSTICS ───────────────────────────────────
[Include this section only if event-table-diagnostics was run]
Omnata App Version: [snow.patch]
Warehouse:          [snow.warehouse.name]
Exception Type:     [EXCEPTION_TYPE]
Exception Message:  [EXCEPTION_MESSAGE]
Last Lifecycle Phase: [last SPAN_EVENT name before failure]

Stack Trace (last frames):
[STACKTRACE — last 3-5 frames]

── WHAT WE HAVE TRIED ────────────────────────────────────────
[List any self-service steps already attempted, or "None yet"]

── SNOWFLAKE ACCOUNT ─────────────────────────────────────────
Snowflake Region:  [CURRENT_REGION() result from Step 1a]
Account ID:        [User to fill in: their Snowflake account identifier]

── PLATFORM STATUS AT TIME OF REPORT ─────────────────────────
Snowflake ([region]): [All systems operational / Active incident: <name and URL>]
Omnata:               [All systems operational / Active incident: <name and URL>]

Please let us know if you need any additional information.

[User signature]
```

Present the filled-in email body and ask the user to:
1. Add their company name to the subject and signature
2. Add their Snowflake account identifier
3. Send to support@omnata.com

#### Option B — Support Portal

Direct the user to:
```
https://omnata.atlassian.net/servicedesk/customer/portal/1/group/1/create/1
```

Map the ticket fields as follows:

| Portal field | Value |
|---|---|
| Summary (title) | Use the subject line from Option A |
| Description | Use the email body from Option A (copy the full text) |
| Affected component | Omnata Sync Engine |

The portal requires an Atlassian account or a portal guest login. If the user does not
have one, email (Option A) is the simpler path.

---

### Step 5: Confirm Submission

Ask the user which option they chose (email or portal) so the interaction is logged.

If they sent the email or submitted the portal form, confirm:
- "Your support ticket has been prepared and is ready to submit / has been submitted"
- Remind them to monitor both https://status.omnata.com/ and https://status.snowflake.com/ for updates
- Note that Omnata support will likely ask for the Snowflake account identifier if not
  already included — make sure it's in the ticket

---

## Stopping Points

- After Step 1 if there is an active Omnata incident that explains the failure
- After Step 2 if the user decides not to raise a ticket (self-service path)
- After Step 4 if the user just needed the formatted ticket text (will submit themselves)
