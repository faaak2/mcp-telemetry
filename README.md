# TelemetryDeck MCP Server

An MCP server that wraps the [TelemetryDeck](https://telemetrydeck.com) analytics API, allowing Claude to query app telemetry data and run analytics using TQL (TelemetryDeck Query Language).

## Installation

### Claude Code

```bash
claude mcp add telemetrydeck --transport http http://localhost:8083/mcp
```

### Claude Desktop

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

## Running the Server

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/)

### Install dependencies

```bash
uv sync
```

### Start the server

```bash
uv run telemetry-deck-mcp
```

The server starts on `http://0.0.0.0:8083` using streamable HTTP transport.

### Run as a systemd service

A service file is included for running the server in production. Copy and enable it:

```bash
sudo cp telemetry-deck-mcp.service /etc/systemd/system/
sudo systemctl enable --now telemetry-deck-mcp
```

### Reverse proxy

The server is designed to sit behind a reverse proxy (e.g. Caddy) at a path like `/telemetry/`. Example Caddy config:

```
mcp-builder.de {
    handle /telemetry/* {
        uri strip_prefix /telemetry
        reverse_proxy localhost:8083
    }
}
```

## Tools

### `run_query`

Execute a TQL query against TelemetryDeck. Pass a full TQL JSON object — supports `timeseries`, `topN`, `groupBy`, `funnel`, `retention`, `scan`, and `experiment` query types.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `bearer_token` | string | Your TelemetryDeck bearer token |
| `app_id` | string | The TelemetryDeck app ID to query |
| `query` | object | Full TQL query object |

**Example query:**

```json
{
  "queryType": "timeseries",
  "dataSource": "CalculatedSignals",
  "filter": {
    "type": "selector",
    "dimension": "appID",
    "value": "<app_id>"
  },
  "aggregations": [
    {"type": "count", "name": "count"}
  ],
  "granularity": "day",
  "intervals": ["2025-01-01/2025-01-31"]
}
```

### `get_insight_query`

Retrieve the TQL query object for a saved insight by its ID. Useful for inspecting or re-executing saved insights.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `bearer_token` | string | Your TelemetryDeck bearer token |
| `app_id` | string | The TelemetryDeck app ID |
| `insight_id` | string | UUID of the saved insight |
| `days_back` | int | Number of days to look back (default: 30) |

## Authentication

Every tool call requires `bearer_token` and `app_id` as parameters. Get your bearer token from the [TelemetryDeck dashboard](https://dashboard.telemetrydeck.com) or via the login API.

## Testing

Use the MCP Inspector to test the server interactively:

```bash
uv run mcp dev src/telemetry_deck_mcp/server.py
```
