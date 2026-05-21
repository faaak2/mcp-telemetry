---
name: telemetrydeck
description: Use when the user wants to pull product analytics, metrics, or insights from TelemetryDeck — phrases like "DAU", "MAU", "retention", "show me signups", "how many users", "metrics for iOS/Web Player", or any mention of "TelemetryDeck" / "telemetry". Handles MCP install, login (including Google-auth via Chrome), and TQL query construction.
---

# TelemetryDeck Metrics

This skill helps the user pull product analytics from TelemetryDeck via TQL queries.

## 1. Capability check

Check whether the TelemetryDeck MCP tools are available in this session. They appear with the prefix `mcp__telemetrydeck__` (e.g. `mcp__telemetrydeck__login`, `mcp__telemetrydeck__run_query`).

- **Not present** → Offer to install it for the user. Ask: "The TelemetryDeck MCP isn't installed yet. Want me to run `claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp`?"

  - If they say yes → run the command via the Bash tool (the user will get a tool-permission prompt from Claude Code itself; that's expected). Once it succeeds, tell them to restart Claude Code and re-ask the question — the new MCP tools only surface after a session restart.
  - If they say no → point them at `references/setup.md` and stop.

  See `references/setup.md` for verification details and troubleshooting.
- **Present** → Continue to the auth check.

## 2. Auth check

`run_query` and `get_insight_query` need a bearer token. Token state is per-conversation:

- If a bearer token was captured earlier in this conversation, reuse it.
- Otherwise run the **login flow**:
  1. Ask: "What's your TelemetryDeck email?"
  2. Ask: "Password?"
  3. Call `mcp__telemetrydeck__login(email, password)`.
  4. **On success** — extract the bearer token from the response. Reply only with "Logged in ✓" — do NOT echo the token back. Continue to the query workflow.
  5. **On 401 or "no password set"** — the account is likely Google-only. Load `references/auth-google.md` and follow it. If the user doesn't have chrome-devtools MCP installed (no `mcp__chrome-devtools__*` tools), offer to install it: "Need chrome-devtools MCP for the Google-auth flow. Want me to run `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`?"

     - If yes → run via the Bash tool, then tell them to restart Claude Code and re-ask. The new tools only surface after a session restart.
     - If no → point them at `references/auth-google.md` and stop.

If at any later point `run_query` / `get_insight_query` returns 401, the token has expired — restart the auth check.

## 3. Query workflow

The MCP server's own instructions describe the order: `get_tql_guide` → `list_apps` → `get_app_structure(app_id)` → `run_query`. Follow it. Specifics:

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
- For time intervals: convert vague user words to ISO interval strings:
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

- **401** → token expired, restart the auth check.
- **TelemetryDeck returns a query error** (bad dimension, unknown source, …) → surface the error message verbatim, propose a corrected query using `get_app_structure`, ask before re-running.
- **Empty result set** → say so explicitly. Do not fabricate numbers.

## 4. Follow-up queries

Once the user has a token and a chosen app, keep both in conversation state. Follow-ups like "now break it down by region" or "and last Tuesday?" skip the discovery steps and go straight to constructing TQL using the cached guide + structure.
