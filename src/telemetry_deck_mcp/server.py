import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from telemetry_deck_mcp.client import TelemetryDeckClient, login as client_login


def _load_tql_guide() -> str:
    return (Path(__file__).parent / "tql_guide.md").read_text(encoding="utf-8")


_TQL_GUIDE = _load_tql_guide()  # used below in `instructions=`; removed in Task 5

mcp = FastMCP(
    "TelemetryDeck",
    host="127.0.0.1",
    port=8083,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", "mcp-builder.de"],
    ),
    instructions=(
        "This server provides access to TelemetryDeck analytics via TQL "
        "(TelemetryDeck Query Language). You MUST read and follow the TQL guide "
        "below before constructing any query.\n\n" + _TQL_GUIDE
    ),
)


@mcp.tool()
async def login(email: str, password: str) -> str:
    """Log in to TelemetryDeck and retrieve a bearer token.

    Use this tool first to authenticate before calling run_query or get_insight_query.
    The returned bearer token can be used for all subsequent API calls.

    Args:
        email: Your TelemetryDeck account email.
        password: Your TelemetryDeck account password.
    """
    try:
        result = await client_login(email, password)
        token = result.get("value", "")
        expires = result.get("expiresAt", "unknown")
        return (
            f"Login successful!\n\n"
            f"Bearer token: {token}\n"
            f"Expires at: {expires}\n\n"
            f"Use this token as the bearer_token parameter in run_query and get_insight_query."
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_tql_guide() -> str:
    """Return the TQL (TelemetryDeck Query Language) reference guide.

    You MUST call this before constructing any query. The guide covers query
    types (timeseries, topN, groupBy, funnel, retention, scan, experiment),
    filters, aggregations, intervals, and granularity.
    """
    return _load_tql_guide()


@mcp.tool()
async def run_query(bearer_token: str, app_id: str, query: dict) -> str:
    """Execute a TQL query against TelemetryDeck.

    The query parameter is a full TQL JSON object. Refer to the TQL guide in
    the server instructions for syntax details. Supported query types:
    timeseries, topN, groupBy, funnel, retention, scan, experiment.

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
    import sys

    transport = "stdio" if "--stdio" in sys.argv else "streamable-http"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
