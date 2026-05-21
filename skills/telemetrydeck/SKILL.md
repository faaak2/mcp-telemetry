---
name: telemetrydeck
description: Use when the user wants to pull product analytics, metrics, or insights from TelemetryDeck — phrases like "DAU", "MAU", "retention", "show me signups", "how many users", "metrics for iOS/Web Player", or any mention of "TelemetryDeck" / "telemetry". Handles MCP install, login (including Google-auth via Chrome), and TQL query construction.
---

# TelemetryDeck Metrics

This skill helps the user pull product analytics from TelemetryDeck via TQL queries. It is a single self-contained file — no reference files required.

## 1. Make sure the MCP server is installed

Check whether the TelemetryDeck MCP tools are available in this session. They appear with the prefix `mcp__telemetrydeck__` (e.g. `mcp__telemetrydeck__login`, `mcp__telemetrydeck__run_query`).

- **Present** → continue to step 2.
- **Not present** → offer to install for the user. Ask: "The TelemetryDeck MCP isn't installed yet. Want me to run `claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp`?"

  - If they say yes → run the command via the Bash tool. The user will see a tool-permission prompt from Claude Code itself; that's expected.
  - If they say no → give them the command to run themselves and stop.

  Once the install succeeds, tell them: "Restart Claude Code and re-ask your question — the new MCP tools only surface after a session restart."

  After the restart, these tools should be available:
  - `mcp__telemetrydeck__login`
  - `mcp__telemetrydeck__run_query`
  - `mcp__telemetrydeck__get_insight_query`
  - `mcp__telemetrydeck__get_tql_guide`
  - `mcp__telemetrydeck__list_apps`
  - `mcp__telemetrydeck__get_app_structure`

  If they don't appear, ask the user to confirm the install completed (`claude mcp list` in their terminal should show `telemetrydeck`).

## 2. Authenticate

`run_query` and `get_insight_query` need a bearer token. Token state is per-conversation:

- If a bearer token was captured earlier in this conversation, reuse it.
- Otherwise run the **email/password login flow**:
  1. Ask: "What's your TelemetryDeck email?"
  2. Ask: "Password?"
  3. Call `mcp__telemetrydeck__login(email, password)`.
  4. **On success** → extract the bearer token from the response. Reply only with "Logged in ✓" — do NOT echo the token back. Continue to step 3.
  5. **On 401 or "no password set"** → the account is likely Google-only. Follow step 2b below.

If at any later point `run_query` / `get_insight_query` returns 401, the token has expired — restart step 2.

### 2b. Capture a bearer token via Google sign-in

Use this when `mcp__telemetrydeck__login(email, password)` returned 401 or "no password set" — the account is Google-only and has no password.

**Check that chrome-devtools MCP is installed.** Look for tools with the prefix `mcp__chrome-devtools__` (e.g. `mcp__chrome-devtools__new_page`).

- **Not present** → offer to install for the user. Ask: "Need chrome-devtools MCP for the Google-auth flow. Want me to run `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`?"

  - If yes → run the command via the Bash tool. Once it succeeds, tell the user to restart Claude Code and re-ask.
  - If no → give them the command to run themselves and stop.

- **Present** → continue.

**Open the dashboard.** Call `mcp__chrome-devtools__new_page("https://dashboard.telemetrydeck.com")`. This opens a browser tab the user can interact with.

**Have the user sign in.** Tell them: "Sign in via Google in the browser tab that just opened, then say 'done'." Wait for confirmation; don't proceed until they say so.

**Capture the token from network traffic.** Once the dashboard loads after sign-in, it makes authenticated API calls to `api.telemetrydeck.com`. Each request carries an `Authorization: Bearer <token>` header.

1. Call `mcp__chrome-devtools__list_network_requests()`.
2. Find any request whose URL is on `api.telemetrydeck.com`.
3. Call `mcp__chrome-devtools__get_network_request(<id-of-that-request>)` to get full details including headers.
4. Read the `Authorization` header — looks like `Bearer eyJhbGciOi...`. Take the part after `Bearer ` — that's the token.

If no `api.telemetrydeck.com` requests appear in the list, ask the user to click around the dashboard (e.g. open one of their apps) so the page makes API calls, then re-list.

**Verify the token works.** Call `mcp__telemetrydeck__list_apps()` (no token needed) and then a small `mcp__telemetrydeck__run_query(...)` using the captured token. If `run_query` returns data, the token is valid. If 401, repeat the network-capture step.

**Hand back.** Reply only with "Logged in ✓" — do NOT echo the token back to the user. Continue to step 3.

**Security note:**
- Never write the token to a file, commit, or visible message.
- Never paste it into any output to the user beyond a brief confirmation.
- On 401 from any later query, restart this Google-sign-in flow.

## 3. Run the query

The MCP server's own instructions describe the order: `get_tql_guide` → `list_apps` → `get_app_structure(app_id)` → `run_query`. Follow it.

### Discover and pick the app

- Call `mcp__telemetrydeck__list_apps()` to see available apps.
- If the user named the app explicitly ("iOS", "Web Player", "the iOS app"), match by `appName` (case-insensitive substring).
- If the user said "the app" / "our app" and there are 2+ apps in the list, **ask which one**. Don't guess.

### Fetch the TQL guide once per session

- Call `mcp__telemetrydeck__get_tql_guide()` on the first query of the session. Cache its content in conversation context for follow-up queries.

### Fetch the app structure for the chosen app

- Call `mcp__telemetrydeck__get_app_structure(app_id)`. It returns `events`, `parameters`, and a description.
- Use this to validate the events and parameters you put into your TQL. If the user asks for an event the app doesn't track, surface the closest matches from the `events` list and ask which they meant.

### Construct TQL

- Follow the guide's syntax exactly.
- For time intervals, convert vague user words to ISO interval strings:
  - "yesterday" → previous calendar day in UTC
  - "this week" → Monday 00:00 UTC of the current week → now
  - "last 30 days" → 30 days ago → now
- Default `granularity` to `day` for timeseries unless the user implies otherwise.

### Execute and present

- Call `mcp__telemetrydeck__run_query(bearer_token, app_id, query)`.
- Present results as readable output — NEVER raw JSON dumps as the primary response:
  - **Timeseries** → small markdown table with `date | metric`, plus a one-line trend summary ("up X% vs the prior period").
  - **topN / groupBy** → ranked markdown table.
  - **Funnel** → `step | count | conversion%`.
  - **Retention** → cohort table.
- Always include the TQL JSON in a collapsible code block at the end so the user can copy it into a saved insight on the dashboard.

### Errors

- **401** → token expired, restart step 2.
- **TelemetryDeck returns a query error** (bad dimension, unknown source, …) → surface the error message verbatim, propose a corrected query using `get_app_structure`, ask before re-running.
- **Empty result set** → say so explicitly. Do not fabricate numbers.

## 4. Follow-up queries

Once the user has a token and a chosen app, keep both in conversation state. Follow-ups like "now break it down by region" or "and last Tuesday?" skip the discovery steps and go straight to constructing TQL using the cached guide + structure.
