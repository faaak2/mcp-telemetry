# TelemetryDeck Skill — Design

**Date:** 2026-05-21
**Status:** Approved, ready for implementation plan

## Goal

Ship a Claude Code skill that teammates can install once to pull product metrics from TelemetryDeck. The skill handles MCP server install, authentication (email/password or Google via Chrome), and end-to-end TQL query construction using server-provided references and per-app structural data.

## Architecture

One skill, branching internally. The skill is a single `SKILL.md` plus two on-demand reference files. The MCP server hosts all the heavy reference material (TQL guide, app metadata) behind dedicated tools rather than dumping it into the per-session `instructions` field.

```
mcp-telemetry/
├── src/telemetry_deck_mcp/
│   ├── server.py                          # 3 new tools, trimmed instructions
│   ├── tql_guide.md                       # unchanged content, no longer inlined
│   ├── iOS-App-StructuralData.json        # unchanged
│   └── Web-Player-StructuralData.json     # unchanged
├── skills/telemetrydeck/                  # NEW
│   ├── SKILL.md
│   └── references/
│       ├── setup.md
│       └── auth-google.md
└── README.md                              # updated install + tool docs
```

Distribution: teammates clone the repo (or copy the `skills/telemetrydeck/` folder) into their `~/.claude/skills/`, then run the MCP-install one-liner from `setup.md`.

## Components

### Server changes (`src/telemetry_deck_mcp/server.py`)

The `instructions` field stops inlining `tql_guide.md`. It becomes a short directive ordering the client to fetch references before querying:

> "TelemetryDeck analytics via TQL. Before constructing any query you MUST: (1) call `get_tql_guide` for the query language reference, (2) call `list_apps` to discover available apps and pick the right `app_id`, (3) call `get_app_structure(app_id)` for the event/parameter list of that app. Compose queries from those, then call `run_query`."

Three new tools, all read static files from the package directory, no auth:

| Tool | Returns | Notes |
| --- | --- | --- |
| `get_tql_guide()` | Contents of `tql_guide.md` | Re-introduces the tool that commit `b81266e` removed. |
| `list_apps()` | `[{appId, appName}, ...]` | Scans for `*-StructuralData.json` and parses each file's top-level `appId` / `appName`. |
| `get_app_structure(app_id)` | Parsed JSON for the matching `appId` | Linear search over the same set. 404-style error if no match. |

Adding a new app: drop a new `*-StructuralData.json` next to the others and redeploy. No code change.

### Skill files

**`skills/telemetrydeck/SKILL.md`**

Frontmatter:

```yaml
---
name: telemetrydeck
description: Use when the user wants to pull product analytics, metrics, or insights from TelemetryDeck — phrases like "DAU", "MAU", "retention", "show me signups", "how many users", "metrics for iOS/Web Player", or any mention of "TelemetryDeck" / "telemetry". Handles MCP install, login (including Google-auth via Chrome), and TQL query construction.
---
```

Body sections (short — heavier material lives in `references/`):

1. **Capability check** — detect whether `mcp__telemetrydeck__*` tools are present. If not, load `references/setup.md` and walk the teammate through install + restart.
2. **Auth check** — reuse a bearer token already captured this session; otherwise enter the auth flow (email/password first, then Google via Chrome on 401).
3. **Query workflow** — follow the MCP server's instructions verbatim: `get_tql_guide` → `list_apps` → `get_app_structure` → `run_query`. Validate event/parameter names against the structure result before submitting. Present results as readable tables or summaries, not raw JSON.
4. **Failure handling** — 401 from any query routes back to auth; query errors are surfaced verbatim with a proposed correction.

**`skills/telemetrydeck/references/setup.md`**

Loaded only when `mcp__telemetrydeck__*` tools are missing.

- One-liner: `claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp`
- Note to restart the Claude Code session so the tools surface
- HTTP version is the default; mentions that local-stdio is available and points at the project README for that path

**`skills/telemetrydeck/references/auth-google.md`**

Loaded only when email/password login returns 401 or "no password set".

1. **chrome-devtools MCP availability check** — if `mcp__chrome-devtools__*` is missing, instruct teammate to install (exact `claude mcp add ...` command verified during implementation) and restart.
2. **Open the dashboard** — `mcp__chrome-devtools__new_page("https://dashboard.telemetrydeck.com")`.
3. **Wait for sign-in** — teammate signs in via Google interactively, then confirms.
4. **Capture the token** — `list_network_requests` filtered to `api.telemetrydeck.com`, pick any request, `get_network_request` it, read the `Authorization` header → extract `Bearer <token>`.
5. **Verify** — call `list_apps` (or another light call) with the captured token to confirm validity before handing back to the query flow.

## User flows

### First-time setup (one-shot per teammate)

```
User: "show me yesterday's signups on Web Player"
Claude: [skill fires]
        [no mcp__telemetrydeck__* tools → loads setup.md]
        "TelemetryDeck MCP isn't installed yet. Run:
         claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp
         then restart Claude Code and re-ask."
```

### Email/password login

```
User: "DAU for iOS this week"
Claude: [skill fires, MCP present, no token yet]
        "What's your TelemetryDeck email?"
User: "..."
Claude: "Password?"
User: "..."
Claude: [calls mcp__telemetrydeck__login → success]
        [calls get_tql_guide, list_apps, get_app_structure("8F4C...")]
        [composes TQL, calls run_query]
        "Mon: 1,204 / Tue: 1,341 / ... (up 8% week-over-week)"
```

### Google-auth fallback

```
User: "DAU for iOS this week"
Claude: [skill fires]
        "Email?" / "Password?"
        [login → 401]
        [loads auth-google.md]
        [no mcp__chrome-devtools__* → instruct install + restart]
After restart:
        [new_page("https://dashboard.telemetrydeck.com")]
        "Sign in via Google in the opened tab, then say 'done'."
User: "done"
Claude: [list_network_requests filtered to api.telemetrydeck.com]
        [get_network_request → Authorization: Bearer ...]
        [list_apps with token → success]
        [proceeds with query flow]
```

### Follow-up query in same session

```
User: "now break it down by region"
Claude: [reuses bearer token + chosen app from session state]
        [reuses cached tql guide + app structure]
        [composes groupBy query, run_query]
        "DE: 540 / US: 412 / ..."
```

## Data flow & state

In-session state held by the skill (conversation-only, never persisted):

- `bearer_token` — captured at auth, reused for all calls until 401
- `chosen_app_id` — the app the teammate is asking about right now
- `tql_guide` — cached return value of `get_tql_guide`
- `app_structure[app_id]` — cached return value of `get_app_structure`

Token expiry handling is reactive only — the skill notes `expiresAt` from `login()` but doesn't proactively refresh; it reacts to 401s by re-entering auth.

## Error handling

| Condition | Skill behaviour |
| --- | --- |
| `mcp__telemetrydeck__*` not present | Load `setup.md`, instruct install + restart |
| `login()` returns 401 / no password | Load `auth-google.md`, run Chrome capture flow |
| `mcp__chrome-devtools__*` not present (in Google path) | Instruct chrome-devtools install + restart |
| `run_query` returns 401 | Treat token as dead, re-enter auth |
| `run_query` returns TQL error | Surface error verbatim, propose corrected query from structure data, ask before re-running |
| User asks for an event the app doesn't track | Surface closest matches from `get_app_structure`, ask |
| Empty result set | Say so explicitly; do not fabricate numbers |
| Ambiguous app reference with 2+ apps | Ask which one; do not guess |

## Security / privacy

- Bearer token never written to a file, commit, or visible output beyond a brief "captured ✓" confirmation.
- Reference files explicitly forbid the model from echoing the token back to the user in plain text.
- Skill never proposes saving credentials or tokens outside the conversation.

## Verification

Manual checkpoints (no automated tests for the skill itself in v1):

1. **Server tools** — `uv run mcp dev src/telemetry_deck_mcp/server.py` locally; confirm `get_tql_guide`, `list_apps`, `get_app_structure` return expected payloads. Must pass before redeploy.
2. **Skill, email/password path** — fresh Claude Code session: trigger phrasing → credentials → small `run_query` succeeds end-to-end.
3. **Skill, Google-auth path** — fresh session with Google-only test account: capture flow completes, captured token successfully runs a query.

Pass criterion for each: the skill reaches a usable result without the operator hand-holding it through a step it should own.

## Files touched

```
src/telemetry_deck_mcp/server.py                # trim instructions; +3 tools
skills/telemetrydeck/SKILL.md                   # NEW
skills/telemetrydeck/references/setup.md        # NEW
skills/telemetrydeck/references/auth-google.md  # NEW
README.md                                       # +skill install section, +tool docs
```

No changes to `client.py` or to the existing `*-StructuralData.json` files.

## Out of scope (v1)

- Persistent token cache across Claude sessions (in-memory only for v1)
- Saving queries as TelemetryDeck insights (only ad-hoc execution via `run_query`)
- Multi-org / multi-account handling beyond a single bearer token
- Automated tests for the skill itself
- A `list_insights` MCP tool (deferred — current `get_insight_query` requires that the teammate already knows the insight UUID)
