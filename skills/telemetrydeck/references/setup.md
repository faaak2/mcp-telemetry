# Install the TelemetryDeck MCP server

The TelemetryDeck MCP server isn't connected to this Claude Code session yet. Install it for the user — don't ask them to run a terminal command themselves.

## Installation

Ask the user for permission first ("Want me to install the TelemetryDeck MCP for you?"), then run via the Bash tool:

```bash
claude mcp add telemetrydeck --transport http https://mcp-builder.de/telemetry/mcp
```

The user will see a tool-permission prompt from Claude Code itself — that's expected.

This adds the hosted HTTP version, which is what most users want. A local stdio version is also available — see the project README at https://github.com/faaak2/mcp-telemetry — but it requires a local Python install.

If the user declines, offer them the command to run themselves and stop.

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
