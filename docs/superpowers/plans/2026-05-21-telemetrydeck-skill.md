# TelemetryDeck Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Claude Code skill teammates install once to pull product metrics from TelemetryDeck, backed by three new MCP-server tools that expose the TQL guide and per-app structural data.

**Architecture:** One skill at `skills/telemetrydeck/` (`SKILL.md` + two `references/` files) that handles MCP install, email/password or Google-auth login (via chrome-devtools MCP), and TQL query construction. The skill stays small because the MCP server's own `instructions` field directs the model to fetch the TQL guide and app structure via three new tools.

**Tech Stack:** Python 3.11+, FastMCP (`mcp[cli]`), httpx (already installed); pytest (added in Task 1); Claude Code skill format (`SKILL.md` + frontmatter).

**Reference:** Design spec at `docs/superpowers/specs/2026-05-21-telemetrydeck-skill-design.md`.

---

### Task 1: Set up pytest harness

The project currently has no tests. Tasks 2–4 use TDD, so add pytest now.

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Add pytest as a dev dependency**

Edit `pyproject.toml`. Append the following block at the end:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Sync dev dependencies**

Run: `uv sync --group dev`
Expected: pytest gets installed; `uv.lock` is updated; no errors.

- [ ] **Step 3: Create empty test package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 4: Add a smoke test**

Create `tests/test_smoke.py`:

```python
def test_pytest_runs():
    assert 1 + 1 == 2
```

- [ ] **Step 5: Run pytest**

Run: `uv run pytest -v`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock tests/__init__.py tests/test_smoke.py
git commit -m "$(cat <<'EOF'
Add pytest harness for upcoming server-tool tests

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Add `get_tql_guide` tool with a testable loader

Refactor the existing `_TQL_GUIDE = ...` module-level read into a function so it's unit-testable, and expose it as an MCP tool.

**Files:**
- Modify: `src/telemetry_deck_mcp/server.py`
- Create: `tests/test_server_tools.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_server_tools.py`:

```python
from telemetry_deck_mcp.server import _load_tql_guide


def test_load_tql_guide_returns_guide_content():
    guide = _load_tql_guide()
    assert guide.startswith("# TQL Complete Reference & Guide")
    assert len(guide) > 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: FAIL with `ImportError: cannot import name '_load_tql_guide' from 'telemetry_deck_mcp.server'`.

- [ ] **Step 3: Implement the loader and tool**

Open `src/telemetry_deck_mcp/server.py`. Replace the current line 7:

```python
_TQL_GUIDE = (Path(__file__).parent / "tql_guide.md").read_text()
```

with:

```python
def _load_tql_guide() -> str:
    return (Path(__file__).parent / "tql_guide.md").read_text()


_TQL_GUIDE = _load_tql_guide()  # used below in `instructions=`; removed in Task 5
```

Then add a new tool after the existing `login` tool (which ends around line 47). Insert:

```python
@mcp.tool()
async def get_tql_guide() -> str:
    """Return the TQL (TelemetryDeck Query Language) reference guide.

    You MUST call this before constructing any query. The guide covers query
    types (timeseries, topN, groupBy, funnel, retention, scan, experiment),
    filters, aggregations, intervals, and granularity.
    """
    return _load_tql_guide()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/telemetry_deck_mcp/server.py tests/test_server_tools.py
git commit -m "$(cat <<'EOF'
Expose TQL guide via a tool, refactor loader for testability

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Add `list_apps` tool

Scans `src/telemetry_deck_mcp/*-StructuralData.json` and returns `{appId, appName}` for each.

**Files:**
- Modify: `src/telemetry_deck_mcp/server.py`
- Modify: `tests/test_server_tools.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_server_tools.py`:

```python
from telemetry_deck_mcp.server import _load_apps


def test_load_apps_returns_known_apps():
    apps = _load_apps()
    names = [a["appName"] for a in apps]
    assert "iOS App" in names
    assert "Web Player" in names
    for a in apps:
        assert set(a.keys()) == {"appId", "appName"}
        assert a["appId"]
        assert a["appName"]
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: previous test still passes; new test FAILs with `ImportError: cannot import name '_load_apps'`.

- [ ] **Step 3: Implement loader and tool**

In `src/telemetry_deck_mcp/server.py`, add this helper near the top (next to `_load_tql_guide`):

```python
def _load_apps() -> list[dict]:
    """Return [{appId, appName}, ...] from bundled StructuralData JSON files."""
    pkg_dir = Path(__file__).parent
    apps = []
    for path in sorted(pkg_dir.glob("*-StructuralData.json")):
        data = json.loads(path.read_text())
        apps.append({"appId": data["appId"], "appName": data["appName"]})
    return apps
```

And add the tool after `get_tql_guide`:

```python
@mcp.tool()
async def list_apps() -> str:
    """List the apps available for querying.

    Call this to discover the `app_id` values you can pass to `run_query`,
    `get_insight_query`, and `get_app_structure`. Returns a JSON array of
    {appId, appName} objects.
    """
    return json.dumps(_load_apps(), indent=2)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/telemetry_deck_mcp/server.py tests/test_server_tools.py
git commit -m "$(cat <<'EOF'
Add list_apps tool for app discovery

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Add `get_app_structure(app_id)` tool

Returns the parsed StructuralData JSON (events + parameters + description) for a given app_id.

**Files:**
- Modify: `src/telemetry_deck_mcp/server.py`
- Modify: `tests/test_server_tools.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_server_tools.py`:

```python
import pytest
from telemetry_deck_mcp.server import _load_app_structure


def test_load_app_structure_returns_events_and_parameters():
    ios_app_id = "8F4C8F44-B281-4316-86C1-627D66367194"
    data = _load_app_structure(ios_app_id)
    assert data["appId"] == ios_app_id
    assert data["appName"] == "iOS App"
    assert isinstance(data["events"], list)
    assert isinstance(data["parameters"], list)
    assert len(data["events"]) > 0


def test_load_app_structure_raises_on_unknown_id():
    with pytest.raises(ValueError, match="not found"):
        _load_app_structure("00000000-0000-0000-0000-000000000000")
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: previous 2 tests pass; new tests FAIL with `ImportError: cannot import name '_load_app_structure'`.

- [ ] **Step 3: Implement loader and tool**

In `src/telemetry_deck_mcp/server.py`, add helper next to `_load_apps`:

```python
def _load_app_structure(app_id: str) -> dict:
    """Return the full parsed StructuralData JSON for the matching app_id."""
    pkg_dir = Path(__file__).parent
    for path in pkg_dir.glob("*-StructuralData.json"):
        data = json.loads(path.read_text())
        if data["appId"] == app_id:
            return data
    raise ValueError(f"App with id {app_id!r} not found")
```

And add the tool after `list_apps`:

```python
@mcp.tool()
async def get_app_structure(app_id: str) -> str:
    """Return the StructuralData (events + parameters) for a given app.

    Call this after `list_apps` to learn which events and parameters are
    available for the app you want to query. The returned JSON has top-level
    keys: `appId`, `appName`, `description`, `exportDate`, `events`,
    `parameters`.

    Args:
        app_id: The TelemetryDeck app ID (from `list_apps`).
    """
    try:
        return json.dumps(_load_app_structure(app_id), indent=2)
    except ValueError as e:
        return f"Error: {e}"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_server_tools.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/telemetry_deck_mcp/server.py tests/test_server_tools.py
git commit -m "$(cat <<'EOF'
Add get_app_structure tool for per-app events and parameters

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Trim the FastMCP `instructions` field

Stop inlining the full 5k-line TQL guide. Replace with a short directive that orders the client to call the new tools.

**Files:**
- Modify: `src/telemetry_deck_mcp/server.py`

- [ ] **Step 1: Replace the `instructions=` argument and remove the now-unused module variable**

In `src/telemetry_deck_mcp/server.py`, find the `mcp = FastMCP(` call (currently lines 9–22). Replace the entire `instructions=(...)` argument with:

```python
    instructions=(
        "TelemetryDeck analytics via TQL (TelemetryDeck Query Language). "
        "Before constructing any query you MUST:\n"
        "  1. Call `get_tql_guide` for the query language reference.\n"
        "  2. Call `list_apps` to discover available apps and pick the right `app_id`.\n"
        "  3. Call `get_app_structure(app_id)` for the event/parameter list of that app.\n"
        "Then compose your TQL and call `run_query`. If `run_query` returns 401, "
        "the bearer token is expired — re-authenticate."
    ),
```

Then delete the line added in Task 2:

```python
_TQL_GUIDE = _load_tql_guide()  # used below in `instructions=`; removed in Task 5
```

`_load_tql_guide` itself stays — `get_tql_guide` still calls it.

- [ ] **Step 2: Manually smoke-test with MCP Inspector**

Run in one terminal: `uv run mcp dev src/telemetry_deck_mcp/server.py`

Open the URL it prints in a browser. In the MCP Inspector:

- **Verify the tool list** contains: `login`, `run_query`, `get_insight_query`, `get_tql_guide`, `list_apps`, `get_app_structure`.
- **Verify the server instructions** are the new short directive — not the full guide (which used to be thousands of lines).
- **Call `get_tql_guide()`** — the result should start with `# TQL Complete Reference & Guide`.
- **Call `list_apps()`** — should return JSON with two entries: iOS App and Web Player.
- **Call `get_app_structure("8F4C8F44-B281-4316-86C1-627D66367194")`** — should return the iOS App JSON with `events` and `parameters` arrays.

Stop the inspector (Ctrl-C) once verified.

- [ ] **Step 3: Run all tests**

Run: `uv run pytest -v`
Expected: all 5 tests pass (1 smoke + 4 server-tool).

- [ ] **Step 4: Commit**

```bash
git add src/telemetry_deck_mcp/server.py
git commit -m "$(cat <<'EOF'
Trim server instructions, direct clients to fetch reference tools

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Create the skill `SKILL.md`

**Files:**
- Create: `skills/telemetrydeck/SKILL.md`

- [ ] **Step 1: Write the file**

Create `skills/telemetrydeck/SKILL.md` with exactly this content:

````markdown
---
name: telemetrydeck
description: Use when the user wants to pull product analytics, metrics, or insights from TelemetryDeck — phrases like "DAU", "MAU", "retention", "show me signups", "how many users", "metrics for iOS/Web Player", or any mention of "TelemetryDeck" / "telemetry". Handles MCP install, login (including Google-auth via Chrome), and TQL query construction.
---

# TelemetryDeck Metrics

This skill helps the user pull product analytics from TelemetryDeck via TQL queries.

## 1. Capability check

Check whether the TelemetryDeck MCP tools are available in this session. They appear with the prefix `mcp__telemetrydeck__` (e.g. `mcp__telemetrydeck__login`, `mcp__telemetrydeck__run_query`).

- **Not present** → Load `references/setup.md` and walk the user through installing the MCP server. After they install + restart Claude Code, they'll re-ask the question and this skill will trigger again with tools available.
- **Present** → Continue to the auth check.

## 2. Auth check

`run_query` and `get_insight_query` need a bearer token. Token state is per-conversation:

- If a bearer token was captured earlier in this conversation, reuse it.
- Otherwise run the **login flow**:
  1. Ask: "What's your TelemetryDeck email?"
  2. Ask: "Password?"
  3. Call `mcp__telemetrydeck__login(email, password)`.
  4. **On success** — extract the bearer token from the response. Reply only with "Logged in ✓" — do NOT echo the token back. Continue to the query workflow.
  5. **On 401 or "no password set"** — the account is likely Google-only. Load `references/auth-google.md` and follow it.

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
````

- [ ] **Step 2: Commit**

```bash
git add skills/telemetrydeck/SKILL.md
git commit -m "$(cat <<'EOF'
Add telemetrydeck skill entrypoint (SKILL.md)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Create `references/setup.md`

**Files:**
- Create: `skills/telemetrydeck/references/setup.md`

- [ ] **Step 1: Write the file**

Create `skills/telemetrydeck/references/setup.md` with exactly this content:

````markdown
# Install the TelemetryDeck MCP server

The TelemetryDeck MCP server isn't connected to this Claude Code session yet. Walk the user through installing it.

## Installation

Have the user run, in their terminal:

```bash
claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp
```

This adds the hosted HTTP version, which is what most users want. A local stdio version is also available — see the project README at https://github.com/faaak2/mcp-telemetry — but it requires a local Python install.

## After install

The user needs to **restart their Claude Code session** for the new MCP tools to surface. Once restarted, they re-ask the original question and this skill fires again with the tools available.

## Verifying after restart

Tools with the prefix `mcp__telemetrydeck__` should now be in the available tools list, including:

- `mcp__telemetrydeck__login`
- `mcp__telemetrydeck__run_query`
- `mcp__telemetrydeck__get_insight_query`
- `mcp__telemetrydeck__get_tql_guide`
- `mcp__telemetrydeck__list_apps`
- `mcp__telemetrydeck__get_app_structure`

If they don't appear, ask the user to confirm the install completed without error (`claude mcp list` in their terminal should show `telemetrydeck`).
````

- [ ] **Step 2: Commit**

```bash
git add skills/telemetrydeck/references/setup.md
git commit -m "$(cat <<'EOF'
Add setup reference for telemetrydeck MCP install

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Create `references/auth-google.md`

**Files:**
- Create: `skills/telemetrydeck/references/auth-google.md`

- [ ] **Step 1: Write the file**

Create `skills/telemetrydeck/references/auth-google.md` with exactly this content:

````markdown
# Capture a TelemetryDeck bearer token via Google sign-in

Use this flow when `mcp__telemetrydeck__login(email, password)` returned 401 or a "no password set" error — the account is Google-signup-only.

## 1. Check that chrome-devtools MCP is installed

Look for tools with the prefix `mcp__chrome-devtools__` (e.g. `mcp__chrome-devtools__new_page`).

- **Not present** → tell the user to run, in their terminal:

  ```bash
  claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
  ```

  Then restart Claude Code and re-ask the original question. The skill will fire again.

- **Present** → continue.

## 2. Open the TelemetryDeck dashboard

Call `mcp__chrome-devtools__new_page("https://dashboard.telemetrydeck.com")`. This opens a browser tab the user can interact with.

## 3. Have the user sign in

Tell the user: "Sign in via Google in the browser tab that just opened, then say 'done'."

Wait for their confirmation. Don't proceed until they confirm sign-in is complete.

## 4. Capture the bearer token from network traffic

Once the dashboard loads after sign-in, it makes authenticated API calls to `api.telemetrydeck.com`. Each carries an `Authorization: Bearer <token>` header. Extract the token:

1. Call `mcp__chrome-devtools__list_network_requests()` to list recent requests.
2. Find any request whose URL is on `api.telemetrydeck.com`.
3. Call `mcp__chrome-devtools__get_network_request(<id-of-that-request>)` to get full details, including headers.
4. Read the `Authorization` header — looks like `Bearer eyJhbGciOi...`. Take the part after `Bearer ` — that's the token.

If no `api.telemetrydeck.com` requests appear in the list, ask the user to click around the dashboard (e.g. open one of their apps) so the page makes API calls, then re-run step 1.

## 5. Verify the token works

Call `mcp__telemetrydeck__list_apps()` (no token needed) and then a small `mcp__telemetrydeck__run_query(...)` using the captured token. If `run_query` returns data, the token is valid. If it returns 401, the capture went wrong — repeat from step 4.

## 6. Hand back to the query flow

The token is now valid for this conversation. Reply only with "Logged in ✓" — do NOT echo the token back to the user. Proceed with their original query.

## Security note

- Never write the token to a file, commit, or visible message.
- Never paste it into any output to the user beyond a brief confirmation.
- On 401 from any later query, restart this capture flow.
````

- [ ] **Step 2: Commit**

```bash
git add skills/telemetrydeck/references/auth-google.md
git commit -m "$(cat <<'EOF'
Add auth-google reference for chrome-devtools-based token capture

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Update `README.md`

Document the new tools and explain how teammates install the skill.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the skill install section**

Open `README.md`. After the `## Installation` section (which currently ends around line 27 with the Claude Desktop config block), insert this new section:

```markdown
### Install the bundled skill (optional)

This repo ships a Claude Code skill at `skills/telemetrydeck/` that wraps the MCP tools with a guided workflow for teammates: it handles install, login (email/password or Google-auth via Chrome), and writes TQL queries from natural-language questions.

Copy it into your local skills directory:

```bash
# macOS / Linux
cp -r skills/telemetrydeck ~/.claude/skills/

# Windows (PowerShell)
Copy-Item -Recurse skills/telemetrydeck $env:USERPROFILE\.claude\skills\
```

After restart, ask Claude things like "show me yesterday's signups on Web Player" or "DAU on iOS this week" and the skill triggers.
```

- [ ] **Step 2: Add the new tools to the Tools section**

In `README.md`, the `## Tools` section currently documents `run_query` and `get_insight_query`. **Before** the `### run_query` heading, insert three new subsections:

````markdown
### `get_tql_guide`

Return the TQL (TelemetryDeck Query Language) reference. Has no parameters. Call this once per session before constructing queries.

### `list_apps`

List the apps available for querying. Has no parameters. Returns a JSON array of `{appId, appName}` objects, one per `*-StructuralData.json` file bundled in the package.

### `get_app_structure`

Return the StructuralData (events + parameters + description) for a given app.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `app_id` | string | The TelemetryDeck app ID (from `list_apps`) |

````

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
Document the new MCP tools and the bundled telemetrydeck skill

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Deploy to mcp-builder.de

Push changes and roll the production server forward so teammates installing the MCP get the new tools.

**Files:** none in this repo — this task is operational.

- [ ] **Step 1: Push commits to origin**

```bash
git push
```

Expected: `main` advances on `origin`.

- [ ] **Step 2: Pull on the server**

The production deployment lives at `/home/seka/MCP/telemetry` on SSH host `netcup-root`, run by user `seka`. Pull as that user (the working tree is owned by `seka`, so a direct `git pull` as root fails with "dubious ownership"):

```bash
ssh netcup-root "sudo -u seka -H bash -c 'cd /home/seka/MCP/telemetry && git checkout -- src/telemetry_deck_mcp/__pycache__/ 2>/dev/null; git pull --ff-only'"
```

Expected: fast-forward to the new HEAD, listing the changed `server.py`, new tests, new `skills/` files, and README updates.

- [ ] **Step 3: Sync deps on the server (only if `pyproject.toml` or `uv.lock` changed)**

This task added pytest as a dev dep. Production only needs runtime deps, but to keep the lockfile in sync re-run `uv sync` on the server:

```bash
ssh netcup-root "sudo -u seka -H bash -c 'cd /home/seka/MCP/telemetry && uv sync'"
```

Expected: no errors. (pytest is a dev-group dep, so it won't be installed in the prod venv unless `--group dev` is passed, which is correct.)

- [ ] **Step 4: Restart the service**

```bash
ssh netcup-root "sudo systemctl restart telemetry-deck-mcp"
```

- [ ] **Step 5: Verify the service is up and the new tools are exposed**

```bash
ssh netcup-root "systemctl status telemetry-deck-mcp --no-pager | head -10"
```

Expected: `Active: active (running)` with a recent timestamp; no errors in the last log lines.

Then from your local machine, smoke-test the HTTP endpoint by listing tools (the simplest check is the existing `claude mcp list` if you have the MCP registered, or a quick `curl https://mcp-builder.de/telemetry/mcp` which should return an MCP-server response).

---

### Task 11: End-to-end verification (manual)

The skill is LLM-driven, so this is a manual smoke test against the live server. Run each path in a **fresh Claude Code session** so the skill triggers from a clean state.

**Files:** none.

- [ ] **Step 1: Install the skill locally**

```powershell
Copy-Item -Recurse C:\Users\faaak\Desktop\Workspace\mcp-telemetry\skills\telemetrydeck $env:USERPROFILE\.claude\skills\
```

Verify it's present:

```powershell
ls $env:USERPROFILE\.claude\skills\telemetrydeck
```

Expected: shows `SKILL.md` and `references/`.

- [ ] **Step 2: Verify the MCP is registered**

```bash
claude mcp list
```

Expected: `telemetrydeck` appears, pointing at `https://mcp-builder.de/telemetry/mcp`. If not, register it:

```bash
claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp
```

- [ ] **Step 3: Email/password path**

Start a **fresh** Claude Code session and ask:

> "Show me DAU on iOS this week from TelemetryDeck."

Expected behavior:

1. Skill triggers (you'll see it announced).
2. Capability check passes (MCP tools present).
3. Claude asks for email + password.
4. After `login` succeeds, Claude calls `get_tql_guide` → `list_apps` → `get_app_structure` → `run_query`.
5. Output is a readable table (not raw JSON), with the TQL JSON in a collapsible block.

Pass criterion: the answer appears without you intervening on a step the skill should own.

- [ ] **Step 4: Google-auth path**

Use a TelemetryDeck account that's Google-only (no password set). In a fresh Claude Code session ask the same question.

Expected behavior:

1. Skill triggers, capability check passes.
2. `login` returns 401.
3. Skill loads `auth-google.md`.
4. If `mcp__chrome-devtools__*` is missing, Claude instructs the install and asks for restart. Run the install, restart, and re-ask:

   ```bash
   claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
   ```

5. Claude opens `https://dashboard.telemetrydeck.com` via `new_page`.
6. Sign in via Google, say "done."
7. Claude lists network requests, finds one to `api.telemetrydeck.com`, extracts the bearer token.
8. Verification call (`list_apps` or small `run_query`) succeeds.
9. Original query is answered as in Step 3.

Pass criterion: same as Step 3 — usable answer without hand-holding the model through a step it should own.

- [ ] **Step 5: Follow-up query test**

Within the same session as Step 3 or 4, ask:

> "Now break that down by region."

Expected: Claude reuses the cached token, chosen app, and structure data; skips re-discovery; runs a `groupBy` query; presents a ranked table.

---

## Spec coverage check

| Spec requirement | Implementing task(s) |
| --- | --- |
| Trim `instructions` field, add directive | Task 5 |
| `get_tql_guide` tool | Task 2 |
| `list_apps` tool | Task 3 |
| `get_app_structure` tool | Task 4 |
| `SKILL.md` with frontmatter + 3-section flow | Task 6 |
| `references/setup.md` | Task 7 |
| `references/auth-google.md` | Task 8 |
| README updates (skill install + new tool docs) | Task 9 |
| Email/password login flow | SKILL.md (Task 6); verified Task 11 Step 3 |
| Google-auth fallback via chrome-devtools | references/auth-google.md (Task 8); verified Task 11 Step 4 |
| Follow-up query state (token, app, cached refs) | SKILL.md Section 4 (Task 6); verified Task 11 Step 5 |
| Reactive token refresh on 401 (no proactive refresh) | SKILL.md Section 2 (Task 6) |
| No persistent token cache (v1) | SKILL.md "per-conversation" wording (Task 6) |
| Manual verification checkpoints | Task 11 |
| Production deploy | Task 10 |
