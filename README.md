# TelemetryDeck MCP Server

An MCP server that wraps the [TelemetryDeck](https://telemetrydeck.com) analytics API, allowing Claude to query app telemetry data and run analytics.

## Setup

```bash
uv sync
```

## Usage

### With Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "telemetrydeck": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/telemetry", "telemetry-deck-mcp"]
    }
  }
}
```

### Testing with MCP Inspector

```bash
uv run mcp dev src/telemetry_deck_mcp/server.py
```

## Tools

### `run_query`

Execute a TQL query against TelemetryDeck. Pass a full TQL JSON object — supports timeseries, topN, groupBy, funnel, retention, scan, and experiment query types.

### `get_insight_query`

Retrieve the TQL query object for a saved insight by its ID. Useful for inspecting or re-executing saved insights.

## Authentication

Every tool call requires `bearer_token` and `app_id` as parameters. Get your bearer token from the TelemetryDeck dashboard or via the login API.
