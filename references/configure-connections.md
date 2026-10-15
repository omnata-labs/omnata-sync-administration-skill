---
name: omnata-configure-connections
description: "Create an Omnata connection to an app from SQL, as an alternative to the Omnata UI, and hand off to creating a sync on it. Covers API key, token, service account and OAuth connection methods, from BEGIN_CONNECTION_CREATION through to a tested connection, and editing existing connections. Use when: user wants CoCo to set up syncs end to end instead of using the UI; has just installed the Sync Engine or a plugin and wants to get data flowing; wants to sync data from or to an app that has no connection yet; wants to create, set up or add a connection or credentials for a plugin. Triggers: set up a sync end to end, do it without the UI, configure Omnata for me, get my <app> data into Snowflake, sync <app> to Snowflake, push data to <app>, I just installed the plugin, what next after install, first sync, create connection, new connection, set up connection, connect to <app>, add another connection, second connection, separate test connection, add credentials, edit connection, rotate credentials, update connection credentials, re-authorize OAuth, BEGIN_CONNECTION_EDIT, BEGIN_CONNECTION_CREATION, UPDATE_CONNECTION_OBJECTS, COMPLETE_CONNECTION_CREATION, OAuth connection, service account connection, API key connection."
---

# Configure Connections

Create an Omnata connection with SQL, step by step. The user can always use the Omnata UI instead. This reference is for when they want CoCo to drive it.

If any step behaves differently from what's described here, stop, tell the user what happened, and offer to finish the connection in the Omnata UI.

**Plugin specifics live in the plugin pages.** Each plugin's page (`references/plugins/<plugin_id>.md`, Connection section) holds its methods, where to get each value, app-side access, credential examples and quirks. Read it before Step 1c. If the page has no Connection section, use `CONNECTION_FORM()` and the plugin's docs.

## Working with users

Follow these throughout. The steps below say where each one applies.

- **Know where CoCo is running.** Check whether this is CoCo Desktop or CoCo in Snowsight from the tools available, and only offer options that environment supports (Step 0).
- **CoCo does the work; the user only handles secrets.** CoCo runs all lookups and every non-sensitive step itself. The user only runs SQL when it carries a secret, and only if they choose the template (Step 0). Before running each call, say what it does.
- **Keep secrets out of the chat.** Default to the placeholder template. Offer the secure handoff only when it's available (Step 0). Never ask for a secret in the chat. If one is pasted, don't repeat it, and suggest rotating it. Don't repeat OAuth codes back either.
- **Tell users where to get each value before asking for it.** Give brief hints with direct console links, any APIs or permissions to enable, and app-side access the connection needs, such as sharing a resource with a service account (Step 1c).
- **Show links clearly.** Put any link the user has to open, such as an OAuth login, in the reply text as a labelled link plus a copyable code block, never only inside a question (Step 5).
- **Ask before opening a browser.** Offer "my own browser" or "the agentic browser" (Desktop only). Try to read the result yourself, and fall back to asking the user to copy and paste it (Step 5).
- **Don't change the user's machine without asking.** Give install, upgrade or uninstall commands for the user to run. Commands that need their machine password go in their own terminal (Step 0).
- **Stop and ask when something needs a person.** Spec approval by a higher role, logging in to an app, or sharing a resource in the target app: explain what's needed, then wait for them to confirm.
- **Flag admin approval up front.** Before starting, check CoCo's role and tell the user the connection needs ACCOUNTADMIN to approve its network access (and OAuth integration). Ask how they want to handle it before Step 4 (Step 0).
- **Check the effect, not just the output.** Confirm each step from the account's state (specifications, connection progress, the connection record) before moving on.

## Where this fits

The overall workflow is: install the app and plugin, **create a connection**, **create a sync**, run it. This reference is the connection step, and it hands straight on to the sync.

**When to start here:**
- **The user wants CoCo to set up syncs end to end instead of using the UI.** That's the main trigger. Start with the connection unless a suitable one already exists, then continue to the sync without waiting to be asked.
- **Straight after install.** A connection is usually the first thing a user needs once the plugin is registered.
- **Later, for a new connection.** Users add connections at any time: a second account or instance of the same app, a separate test or production connection, different credentials or permissions, or a new plugin.
- **The user asks for a sync and there's no connection for it.** Create the connection first, then the sync.

**Signals to infer from the request:**
- "Get my <app> data into Snowflake", "sync <app>", "push this table to <app>": they want a sync, so check for a connection first.
- "I just installed it, what now?": no connection yet, so start here.
- "Set it up for me", "do it without the UI", "automate this": they want CoCo to drive the whole workflow, so keep going step to step without stopping for confirmation except where a person is needed.
- A named environment ("test", "prod", "sandbox") or account: decide whether an existing connection fits, or a new one is needed, and set the production flag (Step 1d).

**Check for an existing connection before creating one:**

```sql
SELECT CONNECTION_ID, CONNECTION_SLUG, CONNECTION_NAME, CONNECTION_METHOD, IS_PRODUCTION_ENVIRONMENT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION
WHERE PLUGIN_FQN = '<PLUGIN_FQN>';
```

If one exists, show it and ask whether to use it or create a new one. If the user only wants a sync and the connection is fine, skip to `references/configure-syncs.md`.

## Scope

This reference starts once the plugin is installed and registered. The user completes these steps themselves, as they do today:

1. Install the Omnata Sync Engine and the plugin from the Snowflake Marketplace.
2. Grant the app privileges the install guide asks for (tasks, warehouse, integrations).
3. Register the plugin with the Sync Engine.

Then this reference covers: preflight checks, starting the connection, adding credentials, approving network access, OAuth authorization if needed, and completing (and testing) the connection. For the sync itself, continue with `references/configure-syncs.md`.

## Step 0: How CoCo and the user split the work

**Where CoCo is running.** Before offering choices, work out whether this is CoCo Desktop or CoCo in Snowsight, from the tools available in the session. Some options only exist in Desktop:

| Capability | CoCo Desktop | CoCo in Snowsight |
|---|---|---|
| Run SQL | Yes | Yes |
| Shell commands (`bash`, `!` prefix), `cortex secret`, `snow` CLI | Yes | Assume no |
| Agentic browser (`open_browser`, `browser_evaluate`) | Yes | Assume no |

If a tool isn't available, don't offer the option that needs it. In Snowsight, that means: sensitive values always use the template, and OAuth login always uses the user's own browser with copy and paste. Check the available tools at run time rather than assuming.

**CoCo runs everything except secrets.** CoCo runs all the lookups (plugin, connection methods and fields, existing connections, specifications, progress) and all the non-sensitive steps (`BEGIN_CONNECTION_CREATION`, spec approval, OAuth start and finish, `COMPLETE_CONNECTION_CREATION`) itself, and reads the results. Don't ask the user to run these or paste results back. Before each call, say in a line what it does.

The user only runs SQL when a step carries a secret (API key, token, service account JSON, OAuth client secret), and only if they choose the template below.

Two exceptions, where CoCo hands a step to the user:
- **Privileges.** If a step fails because CoCo's role can't do it (e.g. approving specifications), give the user the SQL to run as a role that can, or the Snowsight steps. Then CoCo checks the result itself.
- **The user asks.** If the user asks to run a step themselves, give them the SQL, then check the result yourself.

**Admin approval.** Every connection needs its network access specification (and, for OAuth, its security integration specification) approved in Step 4, normally by ACCOUNTADMIN. Check this before Step 2, not when Step 4 arrives:

1. Run `SELECT CURRENT_USER(), CURRENT_ROLE()`.
2. Tell the user: "This connection needs ACCOUNTADMIN to approve its network access to <app> (and its OAuth integration). CoCo is running as <role>."
3. Decide who approves:

| Situation | Who approves in Step 4 |
|---|---|
| The user chose the template for secrets, or otherwise asked that sensitive steps not go through CoCo | **The user.** Assume they want the strict flow: they approve as ACCOUNTADMIN themselves (SQL or Snowsight), even if CoCo is running as ACCOUNTADMIN. Don't ask CoCo-approves as an option |
| CoCo is running as ACCOUNTADMIN, and the user hasn't asked for the strict flow | Ask with `ask_user_question`: "CoCo approves as ACCOUNTADMIN" or "I'll approve it myself". Never approve without asking |
| CoCo is running as any other role | **The user, or their admin.** Don't switch roles without asking. Tell them early, so they can line up an admin. If approval by SQL fails for their role, approve in Snowsight or in the Omnata UI |

The secret question comes before Step 3, which is before Step 4. If the user later picks the template, switch to the strict flow even if they earlier said CoCo could approve.

**How sensitive values are handled.** Ask with `ask_user_question` at each step that needs a secret, not up front.

| Option | How it works |
|---|---|
| Template with placeholders (default) | CoCo writes the SQL with placeholders such as `<API_KEY>`. The user fills them in and runs it in a Snowsight worksheet, then says when it's done. CoCo checks the effect itself (Step 3). CoCo never sees the value. Works for everyone |
| Provide it securely to CoCo | The user stores the value locally with `cortex secret store <key> --prompt` (or `--from-file <path>`). CoCo runs the call through the `snow` CLI with the value injected as an environment variable. The value never appears in the chat or in tool parameters. Only offered in CoCo Desktop, and only if the CLI check below passes |

**Why the secure option needs the `snow` CLI.** CoCo's built-in SQL tool can't receive stored secrets. Only shell commands can, through `cortex secret run`. So the value has to reach Snowflake through a local client, the `snow` CLI. Many CoCo Desktop users won't have it set up.

**CLI check, run before offering the secure option.** Run these with the bash tool:

```bash
snow --version
snow sql -c <SNOW_CONNECTION> --format JSON -q "SELECT CURRENT_ACCOUNT(), CURRENT_REGION()"
```

To find `<SNOW_CONNECTION>`, run `snow connection list` and pick the one for this account. Don't print `connections.toml`, since it can hold passwords. If the connection uses browser-based login, tell the user that a Snowflake login page may open in their browser during the check and later secure-path calls, and that they need to approve it.

Offer the secure option only if both succeed, and the account and region match what `SELECT CURRENT_ACCOUNT(), CURRENT_REGION()` returns in CoCo's own session. Otherwise offer only the template, and tell the user why.

**If the check fails, fall back to the template.** Tell the user why, and offer the template path, which works everywhere. If they want to set up the CLI, point them to Snowflake's [Snowflake CLI documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) for installing, upgrading and configuring connections. Don't run installs, upgrades or uninstalls on the user's machine without asking. Two causes specific to this flow:
- **The CLI is too old for the connection's `authenticator`** (e.g. `oauth_authorization_code`). Login fails with errors such as `Password is empty`. The user needs a current version.
- **The `snow` connection points at a different account** from CoCo's session. Pick the matching connection, or add one.

Tell the user before they choose: **in both cases, Snowflake query history will contain the value**, because `UPDATE_CONNECTION_OBJECTS` receives secrets as a plain argument. If that matters, run the step in a session whose query history is restricted, or rotate the credential after setup.

Never ask the user to paste a secret into the chat. If they do, do not repeat it back, and suggest they rotate it.

## Step 1: Preflight checks

**1a. Confirm the plugin is registered and get its FQN and database.**

```sql
SELECT PLUGIN_FQN, PLUGIN_NAME, DATABASE, SCHEMA, SUPPORTED_CONNECTIVITY_OPTIONS
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.PLUGIN
WHERE PLUGIN_FQN ILIKE '%<APP_NAME>%';
```

If no row comes back, the plugin isn't registered. Stop and send the user back to the install steps.

**1b. Read the connection methods and their fields from the plugin.**

Each plugin defines one or more connection methods. Each method has a name, a set of form fields (some marked secret), and optionally an OAuth template. Read them straight from the plugin:

```sql
CALL <PLUGIN_DATABASE>.PLUGIN.CONNECTION_FORM();
```

It returns `{"success": true, "data": [<method>, ...]}`. For each method, use:

| Key | Meaning |
|---|---|
| `name` | Exact method name for Step 2 |
| `fields[]` | Form fields: `name`, `label`, `required`, `secret`, `type`, `help_text`, `default_value` |
| `oauth_template` | `null` for non-OAuth methods. Otherwise the default `oauth_values` for Step 3b: `oauth_grant`, endpoints, scopes, `oauth_client_auth_method`. The client ID and secret in it are placeholder text, not real values |

If the result comes back as `[object Object]`, read it as text with `SELECT TO_JSON($1) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))`. Run that straight after the call, on its own and not in parallel with other queries, or `LAST_QUERY_ID()` points at the wrong query.

Present the methods to the user and ask which one to use. Fields with `"secret": true` go in `connection_secrets`, all others in `connection_parameters`. Fall back to the plugin docs page if the call fails.

**1c. Tell the user where to get each value.** Once a method is chosen, and before asking for any value, give brief numbered hints on where to find each required field, client ID or secret in the target app. Include direct console links where possible, any APIs or permissions to enable first, and any app-side access the connection needs, such as sharing a resource with a service account. Sources, in order:
1. The plugin's page, Connection section.
2. The field's `help_text` from `CONNECTION_FORM`, and the OAuth template's `oauth_docs_url` if set.
3. The plugin's Omnata docs page (`docs.omnata.com`, Apps section). The plugin's `DOCS_URL` is in `DATA_VIEWS.PLUGIN`.
4. General knowledge of the app's admin console, clearly framed as general guidance.

Keep it to a few lines per value, with direct console links (not just menu paths). Mention common blockers, such as org policies that disable key creation or admin-only settings.

**1d. Agree the connection details with the user.**

| Value | Notes |
|---|---|
| Connection name | Human-readable, e.g. `<App> Prod` |
| Connection slug | Kebab-case, unique, e.g. `<app>-prod`. Syncs refer to the connection by this |
| Production environment | `true` for production, `false` for test/dev. Affects branching |
| Connectivity option | `direct` for SaaS apps. `ngrok` and `privatelink` exist for private databases and aren't covered here |

## Step 2: Start the connection

```sql
CALL OMNATA_SYNC_ENGINE.API.BEGIN_CONNECTION_CREATION(
    '<PLUGIN_FQN>',           -- from Step 1a
    '<CONNECTION_NAME>',
    '<CONNECTION_SLUG>',
    'direct',                 -- connectivity option
    '<CONNECTION_METHOD>',    -- exact method name from Step 1b
    <USES_OAUTH>,             -- true if the method has an OAuth template
    <IS_PRODUCTION>,          -- true or false
    NULL                      -- in-progress id, only when retrying
);
```

Parameters are positional, in the order shown.

On success it returns `{"success": true, "data": {...}}`. Keep these values from `data`:

| Field | Used in |
|---|---|
| `CONNECTION_IN_PROGRESS_ID` | Every later step |
| `PLUGIN_DATABASE` | Specification approval, OAuth |
| `EAI_SPEC_NAME` | Approving network access |
| `SI_SPEC_NAME` | Approving the OAuth integration (OAuth only) |
| `OAUTH_SECRET_NAME` | OAuth authorization (OAuth only) |

On failure it returns `{"success": false, "error": "..."}`. A common one is `Connection with slug <slug> already exists`: pick a different slug, or edit the existing connection (see "Edit an existing connection" below).

## Step 3: Add connection parameters and credentials

`UPDATE_CONNECTION_OBJECTS` sends the method's field values to the plugin. The plugin uses them to work out the network addresses it needs and stores secrets in a Snowflake secret it owns.

Shape of each object:
- `connection_parameters`: non-secret fields, `{"<field>": {"value": "<value>"}}`.
- `connection_secrets`: fields marked secret, same shape.
- `oauth_values`: OAuth methods only (see Step 3b). Otherwise pass an empty object.

### 3a. Non-OAuth methods (API key, token, service account)

Ask the Step 0 secret question, then use one of these.

**Template with placeholders.** CoCo builds this from the method's fields (Step 1b) and gives it to the user to fill in and run in a Snowsight worksheet:

```sql
CALL OMNATA_SYNC_ENGINE.API.UPDATE_CONNECTION_OBJECTS(
    <CONNECTION_IN_PROGRESS_ID>,
    OBJECT_CONSTRUCT('<non_secret_field>', OBJECT_CONSTRUCT('value', '<VALUE>')),
    OBJECT_CONSTRUCT('<secret_field>', OBJECT_CONSTRUCT('value', $$<PASTE THE SECRET HERE>$$)),
    OBJECT_CONSTRUCT()
);
```

Repeat key/value pairs inside each `OBJECT_CONSTRUCT` for more fields; use `OBJECT_CONSTRUCT()` if there are none. Tell the user how to fill in each placeholder: paste the value between the `$$` markers unchanged. That keeps multi-line values such as JSON key files as a string. See the plugin's page for a worked example.

**Provide securely to CoCo.**

1. Ask the user to store the value locally, in their own terminal (interactive prompts may not work through CoCo's `!` prefix). For a file:
   ```
   cortex secret store <key> --from-file /path/to/key.json
   ```
   For a short value such as an API key or client secret, `--prompt` asks for it without echoing. One of `--prompt` or `--from-file` is required:
   ```
   cortex secret store <key> --prompt
   ```
   Tell the user to paste once and press Enter once; in testing a double paste stored the value twice. If `cortex` isn't on their PATH, use `~/.local/bin/cortex`. Confirm it was stored without revealing it: `cortex secret run --map <key>=V -- sh -c 'echo ${#V}'` prints only the length.
2. CoCo runs the call with the bash tool, wrapping `snow sql` in `cortex secret run --map`, which injects the stored secret as an environment variable. **Before running it, warn the user** if the `snow` connection uses browser-based login (an `authenticator` such as `externalbrowser` or `oauth_authorization_code`): a Snowflake login page may open in their browser, and they need to approve it for the call to go through. Then wait for the call to finish.
   ```bash
   cortex secret run --map <key>=SECRET_VALUE -- sh -c 'snow sql -c <SNOW_CONNECTION> --format JSON --enable-templating STANDARD -D "secret_value=$SECRET_VALUE" -q "CALL OMNATA_SYNC_ENGINE.API.UPDATE_CONNECTION_OBJECTS(<CONNECTION_IN_PROGRESS_ID>, OBJECT_CONSTRUCT(), OBJECT_CONSTRUCT(\$\$<secret_field>\$\$, OBJECT_CONSTRUCT(\$\$value\$\$, \$\$<% secret_value %>\$\$)), OBJECT_CONSTRUCT())"'
   ```
   The command text holds only the variable name, never the value.
3. Rules:
   - **Always pass `--format JSON --enable-templating STANDARD`.** With the default table output, `snow sql` prints the whole statement after substitution, including the secret, into CoCo's tool output. JSON output doesn't. Without `STANDARD`, any `&` in the SQL, such as `&prompt=consent` in an OAuth URL, is read as legacy `&{}` templating, and the call fails with `The SQL query mixes &{ ... } syntax and <% ... %> syntax`.
   - **Don't print the raw output.** The proc result doesn't echo `oauth_client_secret`, but pipe the output through a redaction filter anyway (e.g. `sed -E` on the secret's known prefix; the plugin page lists it where known), and print only `success` and `error`.
   - **Check the effect, not just the output.** After `UPDATE_CONNECTION_OBJECTS`, `SHOW SPECIFICATIONS IN APPLICATION <PLUGIN_DATABASE>` should show the EAI spec on a new `sequence_number` with the plugin's hosts in `HOST_PORTS`, and for OAuth a new `SECURITY_INTEGRATION` spec. If the hosts list is still empty, the update didn't run.
   - **Use `cortex secret run --map`, not the bash tool's `secret_env`.** In testing, `secret_env` left the variable empty.
   - **Wrap the substituted value in `$$...$$`.** Multi-line JSON with newlines, escaped quotes and apostrophes arrived byte-for-byte (verified by SHA-256 on both sides). Also use `$$...$$` for the other string literals in the `-q` text, so the shell's single quotes stay balanced.
   - `cortex secret run` drops a single trailing newline from file-stored values. That's harmless for JSON keys and tokens.
   - **Validate the stored value without revealing it** before sending: print its length, and for structured values check the expected shape (e.g. a JSON key parses and has its expected keys). Non-secret parts, such as a service account email, can be shown to the user.
4. After the connection is complete, offer `cortex secret delete <key>`.

Template path: when the user says they've run it, check the effect yourself (the spec check below) rather than asking for the output. Secure path: check the result for `"success": true`.

### 3b. OAuth methods

For OAuth, `connection_secrets` is usually empty and the credentials go in `oauth_values`:

| Key | Source |
|---|---|
| `oauth_grant` | From the plugin's OAuth template: `authorization_code` or `client_credentials` |
| `oauth_client_id` | User, from their OAuth app in the target app's developer console |
| `oauth_client_secret` | User. **Sensitive**, use the Step 0 secret question |
| `oauth_token_endpoint` | From the plugin's OAuth template |
| `oauth_authorization_endpoint` | From the template (authorization code only) |
| `oauth_allowed_scopes` | From the template, as an array |
| `oauth_client_auth_method` | From the template, e.g. `CLIENT_SECRET_POST` (default) or `CLIENT_SECRET_BASIC` |

Before Step 5, the user must allow Snowflake's redirect URI in their OAuth app. It depends on where the login starts:
- **CoCo route (`SYSTEM$START_OAUTH_FLOW` from SQL):** the account URL plus `/oauth/complete-secret`, e.g. `https://<orgname>-<account_name>.snowflakecomputing.com/oauth/complete-secret`.
- **Snowsight route (the app's authorization request, as used by the Omnata UI):** `https://apps-api.c1.<region>.app.snowflake.com/oauth/complete-secret`, where `<region>` is the Snowsight region host, e.g. `ap-southeast-2.aws`.

Recommend adding both, if the OAuth app allows several. To get the exact CoCo-route value, run Step 5's `SYSTEM$START_OAUTH_FLOW` and read `redirect_uri` from the returned URL. Starting the flow does nothing until the user completes it. Have the user add the URI before they open the login link.

Build the call from the plugin's `oauth_template` (Step 1b); the plugin's page has a worked example. With the template path, the user fills in the client ID and secret and runs it.

```sql
CALL OMNATA_SYNC_ENGINE.API.UPDATE_CONNECTION_OBJECTS(
    <CONNECTION_IN_PROGRESS_ID>,
    OBJECT_CONSTRUCT(),
    OBJECT_CONSTRUCT(),
    OBJECT_CONSTRUCT(
        'oauth_grant', '<from template>',
        'oauth_client_id', '<CLIENT_ID>',
        'oauth_client_secret', '<CLIENT_SECRET>',
        'oauth_token_endpoint', '<from template>',
        'oauth_authorization_endpoint', '<from template>',
        'oauth_allowed_scopes', ARRAY_CONSTRUCT('<scope>', ...),
        'oauth_client_auth_method', '<from template>'
    )
);
```

For the secure path, store the client secret with `cortex secret store <key> --prompt` and substitute it into `oauth_client_secret` the same way as in 3a. Authorization endpoints often contain `&` query parameters, which is why `--enable-templating STANDARD` is required.

## Step 4: Approve network access (and the OAuth integration)

The plugin creates an application specification asking for access to its hosts. OAuth methods also get a security integration specification. Both must be approved on the **plugin app**, not the Sync Engine.

**4a. Check the specifications.**

```sql
SHOW SPECIFICATIONS IN APPLICATION <PLUGIN_DATABASE>;
```

Find the rows whose `name` matches `EAI_SPEC_NAME` (type `EXTERNAL_ACCESS`) and, for OAuth, `SI_SPEC_NAME` (type `SECURITY_INTEGRATION`). Snowflake sometimes assigns a numeric name. If no name matches, use the only row of the expected type. Note each row's `sequence_number` and show the user the requested hosts.

**4b. Approve.** Follow the approver decided in Step 0 (Admin approval). Re-check `SELECT CURRENT_ROLE()` first.
- **CoCo approves** (only if the user agreed, and CoCo is ACCOUNTADMIN): show the requested hosts (and, for OAuth, the integration's endpoints and scopes), say CoCo is approving them as ACCOUNTADMIN, then run the SQL below.
- **The user approves:** show the same details, and give them the SQL below with the spec names and sequence numbers filled in, to run as ACCOUNTADMIN. Or give the Snowsight steps. Then wait for them to confirm, and check with 4c.

Approve every pending spec for this connection: the EAI spec, and for OAuth the SI spec. Use each one's current `sequence_number`; after Step 3 the EAI spec is usually on sequence 2.

- **By SQL** (as ACCOUNTADMIN):
  ```sql
  ALTER APPLICATION <PLUGIN_DATABASE> APPROVE SPECIFICATION <SPEC_NAME> SEQUENCE_NUMBER = <SEQUENCE_NUMBER>;
  ```
- **In Snowsight**: Data Products, Apps, open the plugin app, approve the pending request.

**4c. Confirm.**

```sql
CALL OMNATA_SYNC_ENGINE.API.PLUGIN_CHECK_CONNECTION_PROGRESS(<CONNECTION_IN_PROGRESS_ID>);
```

Returns `latest_eai_spec_revision_approved` (must be `true`), plus for OAuth `latest_si_spec_revision_approved` and `oauth_secret_configuration_done`.

## Step 5: Authorize OAuth (authorization code only)

Skip this step for non-OAuth methods and for `client_credentials`. A person has to log in to the app in a browser. Use Route A by default; Route B is the fallback.

**Route A: login link from CoCo.**

1. Start the flow:
   ```sql
   SELECT SYSTEM$START_OAUTH_FLOW('<PLUGIN_DATABASE>.DATA.<OAUTH_SECRET_NAME>');
   ```
   It returns the app's login URL. Check that its `redirect_uri` is on the OAuth app's allowed list (see Step 3b).
2. **Always show the link.** First, in your text response (never only inside an `ask_user_question` prompt), display the URL:
   - as a clickable markdown link with a clear label, on its own line, e.g. **[Open the <App> login for <CONNECTION_NAME>](<URL>)**, and
   - in a fenced code block underneath, so it can be copied in full.
3. **Stop and ask how to open it.** Use `ask_user_question`, offering only the options the current environment supports (see "Where CoCo is running" in Step 0):

   | Option | Offer when |
   |---|---|
   | Open it in my own browser | Always |
   | CoCo opens it in the agentic browser | Only in CoCo Desktop (the `open_browser` and `browser_evaluate` tools are available) |

4. **Agentic browser route.**
   1. Call `open_browser` with the URL. The user logs in and approves in the browser panel. CoCo never types their credentials.
   2. Ask them to leave the panel on the Snowflake page and say when they're done.
   3. Read the address with `browser_evaluate` (`window.location.href`). Don't rely on `browser_tabs`; in testing it showed no tabs while the panel was open.
   4. **If CoCo can't read it** (the panel closed, the address isn't the `complete-secret` page, or the tool errors), fall back to asking the user to copy and paste the address bar URL. If the attempt is lost, start a fresh flow, since the link is single-use.
5. **Own-browser route.** Show the link again in this same message, as in item 2 (labelled link, then the full URL in a code block), followed by numbered instructions: open it, approve, then paste back the address bar URL of the page they land on, in their next message. Never refer to "the link above": the question in item 3 can push the earlier link out of view.

   The link is single-use. If the attempt is lost, for example the page closed before CoCo read it, run `SYSTEM$START_OAUTH_FLOW` again for a fresh URL, then show and ask again.
6. The browser lands on Snowflake's `.../oauth/complete-secret?state=...&code=...` page. The page may be blank or show an error, which is fine. The address holds a one-time code; don't repeat it back to the user. Check that its `state` matches the URL you generated.
7. Finish with the query string (everything after `?`):
   ```sql
   SELECT SYSTEM$FINISH_OAUTH_FLOW('<QUERY_STRING_AFTER_QUESTION_MARK>');
   ```
   It returns `OAuth flow successfully completed.`

**Route B: Snowsight.** Open the plugin app in Snowsight and complete the pending secret authorization request, which runs the same login. If this doesn't complete the login, go back to Route A, or finish the connection in the Omnata UI.

After Route A, `PLUGIN_CHECK_CONNECTION_PROGRESS` still shows `oauth_secret_configuration_done: false`. That flag tracks the Snowsight authorization request (Route B), which Route A bypasses, so it's expected. Go straight to Step 6, whose connection test is the real check that the token works.

## Step 6: Complete the connection

```sql
CALL OMNATA_SYNC_ENGINE.API.COMPLETE_CONNECTION_CREATION(<CONNECTION_IN_PROGRESS_ID>);
```

This enables network access, binds the plugin to its integration and secrets, runs the plugin's own connection test against the app, and creates the connection record. **A success result means the credentials work.** There is no separate test-connection procedure available to customer roles.

Confirm:

```sql
SELECT CONNECTION_ID, CONNECTION_SLUG, CONNECTION_NAME, CONNECTION_METHOD, IS_PRODUCTION_ENVIRONMENT
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.CONNECTION
WHERE CONNECTION_SLUG = '<CONNECTION_SLUG>';
```

If it fails, the error usually comes from the plugin's connection test (wrong credentials, missing scopes, unapproved hosts). Fix the cause, re-run Step 3 with corrected values if needed, then run Step 6 again. The in-progress connection stays open between attempts.

## Step 7: Next, a sync

Creating a sync is the natural next step. Don't stop at a successful connection:
- If the user asked for an end-to-end setup, or already named the data they want, go straight on with `references/configure-syncs.md`. Carry over the connection slug and any details they already gave (which data, direction, target, schedule).
- Otherwise, offer it: "The connection is ready. Do you want to set up a sync on it now?"

Then create the sync, run it once, and confirm the run was healthy and loaded records. That's the end of the end-to-end workflow.

If the run comes back `FAILED`, read the per-stream error:

```sql
SELECT TO_JSON(INBOUND_GLOBAL_ERROR_BY_STREAM) AS STREAM_ERRORS, GLOBAL_ERROR
FROM OMNATA_SYNC_ENGINE.DATA_VIEWS.SYNC_RUN
WHERE SYNC_RUN_ID = <SYNC_RUN_ID>;
```

Explain the error in plain terms and check the plugin page's notes for known causes. Then tell the user what to change in the app or the sync, and rerun. A failed first run on a new connection is usually about the data or the sync settings, not the connection.

To remove a test sync, `DELETE_SYNC('<sync_slug>', NULL)` deletes the sync record, its raw table and its normalized view in one call, and leaves the connection and other syncs alone. For a full clean-up of syncs and a connection, see "Clean Up Syncs and Connections" in `references/actions.md`.

## Edit an existing connection

Use this to rotate credentials, change connection parameters, rename a connection, change its production flag, or re-authorize OAuth. The connection keeps its ID and slug, so its syncs carry on using it.

The edit follows the same steps as creating a connection, with `BEGIN_CONNECTION_EDIT` instead of `BEGIN_CONNECTION_CREATION`. All of Step 0 applies: CoCo does the lookups, the user handles secrets, and the admin approval check comes up front.

1. **Find the connection** in `DATA_VIEWS.CONNECTION` (its `CONNECTION_ID`, name, slug, method and production flag), and confirm with the user what they want to change.
2. **Start the edit:**
   ```sql
   CALL OMNATA_SYNC_ENGINE.API.BEGIN_CONNECTION_EDIT(
       '<CONNECTION_NAME>',      -- current or new name
       '<CONNECTION_SLUG>',      -- keep the existing slug
       <CONNECTION_ID>,
       <NEW_SECURITY_INTEGRATION>, -- OAuth only: true to replace the OAuth integration (e.g. new client ID/secret or scopes); otherwise false
       <NEW_OAUTH_SECRET>,       -- OAuth only: true to log in again and get fresh tokens; otherwise false
       <IS_PRODUCTION>,          -- current or new value
       NULL                      -- in-progress id, only when retrying
   );
   ```
   It returns the same fields as Step 2, including a new `CONNECTION_IN_PROGRESS_ID`. The plugin's replacement objects alternate between `__A` and `__B` name suffixes, and start from the connection's current secrets and network addresses.
3. **Send only what changes** with `UPDATE_CONNECTION_OBJECTS` (Step 3), using the same secret options. Leave out secret fields that aren't changing; their saved values are kept. To change nothing but the name or production flag, this step can be skipped.
4. **Approve if needed** (Step 4). If the network addresses didn't change, the existing approved specification stays valid and `PLUGIN_CHECK_CONNECTION_PROGRESS` already shows it approved. If they changed, or the OAuth integration is being replaced, approve the new revision.
5. **OAuth re-authorization:** if `NEW_OAUTH_SECRET` or `NEW_SECURITY_INTEGRATION` is true, run the login again (Step 5).
6. **Complete** with `COMPLETE_CONNECTION_CREATION(<CONNECTION_IN_PROGRESS_ID>)` (Step 6). This runs the connection test, switches the connection to the new objects and disables the old ones.
7. **Confirm** `DATA_VIEWS.CONNECTION` shows the new object names (the other suffix), then run one of the connection's syncs to check it still works.

To abandon an edit, use `CANCEL_CONNECTION_CREATION('<CONNECTION_SLUG>')`. The existing connection stays as it was. If an OAuth re-authorization edit doesn't behave as described, finish it in the Omnata UI.

## Retry and cancel

- **Retry Step 2 for the same connection**: pass the existing in-progress ID as the last argument of `BEGIN_CONNECTION_CREATION`. This updates the in-progress record in place. If the retry fails, cancel the connection (below) and start again with a new slug.
- **Abandon a connection in progress**: removes the in-progress connection and the plugin's pending or approved specifications for it. The slug can then be reused, but **not for 15 minutes**: Snowflake won't recreate an application specification with the same name within 15 minutes of dropping it, and `BEGIN_CONNECTION_CREATION` fails with `Cannot recreate an application specification within 15 minutes after dropping a specification with the same name`. To restart straight away, use a new slug.
  ```sql
  CALL OMNATA_SYNC_ENGINE.API.CANCEL_CONNECTION_CREATION('<CONNECTION_SLUG>');
  ```
- **Leave a blank secret field to keep its saved value**: `UPDATE_CONNECTION_OBJECTS` merges with secrets saved on earlier calls.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `Connection with slug ... already exists` | Slug in use | Choose a new slug |
| `Cannot recreate an application specification within 15 minutes...` | The slug's connection was cancelled or deleted less than 15 minutes ago | Wait 15 minutes, or use a new slug |
| Insufficient privileges on `ALTER APPLICATION ... APPROVE SPECIFICATION` | Role can't approve app specs | Approve in Snowsight, or switch to ACCOUNTADMIN |
| `latest_eai_spec_revision_approved` stays false | Approved an older revision, or the wrong spec | Re-run `SHOW SPECIFICATIONS`, approve the latest `sequence_number` |
| `Missing option(s): [OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET]` | OAuth method with empty `oauth_values` | Re-run Step 3b with the OAuth values |
| OAuth login returns a redirect URI error | Snowflake redirect URI not allowed in the OAuth app | Add it in the app's OAuth settings, then retry Step 5 |
| `COMPLETE_CONNECTION_CREATION` fails with an auth error | Wrong credentials, or missing app-side access (e.g. a resource not shared with the service account) | Fix the credential or access, re-run Step 3, then Step 6 |

## Notes

- Everything here runs through the Sync Engine's API procedures (`OMNATA_SYNC_ENGINE.API`), which run as the app. CoCo never creates network rules, integrations or secrets directly; the plugin owns those.
- All procedures return `{"success": ..., "data" | "error": ...}` instead of throwing. Always check `success`.
