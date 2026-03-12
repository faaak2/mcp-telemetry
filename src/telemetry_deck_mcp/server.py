import json
from mcp.server.fastmcp import FastMCP
from telemetry_deck_mcp.client import TelemetryDeckClient

mcp = FastMCP("TelemetryDeck", host="0.0.0.0", port=8083)


@mcp.tool()
async def run_query(bearer_token: str, app_id: str, query: dict) -> str:
    """Execute a TQL query against TelemetryDeck.

    The query parameter is a full TQL JSON object. TQL supports these query types:
    timeseries, topN, groupBy, funnel, retention, scan, experiment.

    Example minimal timeseries query:
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

    Args:
        bearer_token: Your TelemetryDeck bearer token (from dashboard or login).
        app_id: The TelemetryDeck app ID to query.
        query: Full TQL query object as a dict.
    """
    try:
        client = TelemetryDeckClient(bearer_token, app_id)
        result = await client.run_query(query)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_insight_query(
    bearer_token: str, app_id: str, insight_id: str, days_back: int = 30
) -> str:
    """Get the TQL query object for a saved TelemetryDeck insight.

    Returns the TQL JSON that the insight would execute. You can inspect it
    or pass it to run_query to execute it.

    Args:
        bearer_token: Your TelemetryDeck bearer token.
        app_id: The TelemetryDeck app ID.
        insight_id: The UUID of the saved insight.
        days_back: Number of days to look back (default 30).
    """
    try:
        client = TelemetryDeckClient(bearer_token, app_id)
        result = await client.get_insight_query(insight_id, days_back)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error: {e}"


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
