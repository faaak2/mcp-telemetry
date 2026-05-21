import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from telemetry_deck_mcp.client import TelemetryDeckClient, login as client_login


def _load_tql_guide() -> str:
    return (Path(__file__).parent / "tql_guide.md").read_text(encoding="utf-8")


def _load_apps() -> list[dict]:
    """Return [{appId, appName}, ...] from bundled StructuralData JSON files."""
    pkg_dir = Path(__file__).parent
    apps = []
    for path in sorted(pkg_dir.glob("*-StructuralData.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        apps.append({"appId": data["appId"], "appName": data["appName"]})
    return apps


def _load_app_structure(app_id: str) -> dict:
    """Return the full parsed StructuralData JSON for the matching app_id."""
    pkg_dir = Path(__file__).parent
    for path in pkg_dir.glob("*-StructuralData.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["appId"] == app_id:
            return data
    raise ValueError(f"App with id {app_id!r} not found")



mcp = FastMCP(
    "TelemetryDeck",
    host="127.0.0.1",
    port=8083,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", "mcp-builder.de"],
    ),
    instructions=(
        "TelemetryDeck analytics via TQL (TelemetryDeck Query Language). "
        "Before constructing any query you MUST:\n"
        "  1. Call `get_tql_guide` for the query language reference.\n"
        "  2. Call `list_apps` to discover available apps and pick the right `app_id`.\n"
        "  3. Call `get_app_structure(app_id)` for the event/parameter list of that app.\n"
        "Then compose your TQL and call `run_query`. If `run_query` returns 401, "
        "the bearer token is expired — re-authenticate.\n\n"
        "Query scoping is handled automatically: do NOT set `dataSource`, "
        "`appID`, or an `appID` filter in your query. `run_query` resolves the "
        "correct namespaced dataSource for the org and adds an `appID` selector "
        "filter for the `app_id` you pass. Setting these yourself can produce "
        "silently-wrong results (e.g. zero samples for events that clearly exist)."
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
async def list_apps() -> str:
    """List the apps available for querying.

    Call this to discover the `app_id` values you can pass to `run_query`,
    `get_insight_query`, and `get_app_structure`. Returns a JSON array of
    {appId, appName} objects.
    """
    return json.dumps(_load_apps(), indent=2)


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
