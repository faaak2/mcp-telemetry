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
