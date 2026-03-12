import json
import httpx
from mcp.server.fastmcp import FastMCP
from telemetry_deck_mcp.client import TelemetryDeckClient

mcp = FastMCP(
    "TelemetryDeck",
    host="0.0.0.0",
    port=8083,
    instructions=(
        "This server provides access to TelemetryDeck analytics via TQL "
        "(TelemetryDeck Query Language). Before constructing your first TQL query "
        "in a session, you MUST call the get_tql_docs tool to read the TQL "
        "documentation. Start with the 'query' topic for the general reference, "
        "then fetch additional topics as needed for your specific query type."
    ),
)

TQL_DOCS = {
    "firstGuideline": "https://telemetrydeck.com/docs/tql/firstGuideline/",
    "query": "https://telemetrydeck.com/docs/tql/query/",
    "queryType": "https://telemetrydeck.com/docs/tql/queryType/",
    "timeseries": "https://telemetrydeck.com/docs/tql/timeseries/",
    "topN": "https://telemetrydeck.com/docs/tql/topN/",
    "groupBy": "https://telemetrydeck.com/docs/tql/groupBy/",
    "scan": "https://telemetrydeck.com/docs/tql/scan/",
    "funnel": "https://telemetrydeck.com/docs/tql/funnel/",
    "experiment": "https://telemetrydeck.com/docs/tql/experiment/",
    "retention": "https://telemetrydeck.com/docs/tql/retention/",
    "granularity": "https://telemetrydeck.com/docs/tql/granularity/",
    "time-intervals": "https://telemetrydeck.com/docs/tql/time-intervals/",
    "descending": "https://telemetrydeck.com/docs/tql/descending/",
    "baseFilters": "https://telemetrydeck.com/docs/tql/baseFilters/",
    "filters": "https://telemetrydeck.com/docs/tql/filters/",
    "aggregators": "https://telemetrydeck.com/docs/tql/aggregators/",
    "post-aggregators": "https://telemetrydeck.com/docs/tql/post-aggregators/",
    "dimensionSpec": "https://telemetrydeck.com/docs/tql/dimensionSpec/",
    "extractionFunction": "https://telemetrydeck.com/docs/tql/extractionFunction/",
    "topNMetricSpec": "https://telemetrydeck.com/docs/tql/topNMetricSpec/",
    "valueFormatter": "https://telemetrydeck.com/docs/tql/valueFormatter/",
    "queryContext": "https://telemetrydeck.com/docs/tql/queryContext/",
}


@mcp.tool()
async def get_tql_docs(topic: str = "query") -> str:
    """Fetch TQL documentation from TelemetryDeck.

    Call this tool before writing your first TQL query to understand the syntax.
    Start with 'query' for the general reference, then fetch specific topics as needed.

    Available topics: firstGuideline, query, queryType, timeseries, topN, groupBy,
    scan, funnel, experiment, retention, granularity, time-intervals, descending,
    baseFilters, filters, aggregators, post-aggregators, dimensionSpec,
    extractionFunction, topNMetricSpec, valueFormatter, queryContext

    Args:
        topic: The documentation topic to fetch (default: 'query').
    """
    if topic not in TQL_DOCS:
        return (
            f"Unknown topic '{topic}'. Available topics: {', '.join(TQL_DOCS.keys())}"
        )

    url = TQL_DOCS[topic]
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            from html.parser import HTMLParser

            class DocExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_article = False
                    self.depth = 0
                    self.text_parts = []
                    self.skip_tags = {"script", "style", "nav", "header", "footer"}
                    self.skip_depth = 0

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "article" or (
                        tag in ("div", "main")
                        and any(
                            c in attrs_dict.get("class", "")
                            for c in ("content", "article", "docs", "markdown")
                        )
                    ):
                        self.in_article = True
                        self.depth = 0
                    if self.in_article:
                        self.depth += 1
                    if tag in self.skip_tags:
                        self.skip_depth += 1
                    if tag in ("h1", "h2", "h3", "h4"):
                        self.text_parts.append("\n\n## " if tag == "h2" else "\n\n### " if tag in ("h3", "h4") else "\n\n# ")
                    elif tag == "p":
                        self.text_parts.append("\n\n")
                    elif tag == "li":
                        self.text_parts.append("\n- ")
                    elif tag == "code":
                        self.text_parts.append("`")
                    elif tag == "pre":
                        self.text_parts.append("\n```\n")
                    elif tag == "br":
                        self.text_parts.append("\n")

                def handle_endtag(self, tag):
                    if self.in_article:
                        self.depth -= 1
                        if self.depth <= 0:
                            self.in_article = False
                    if tag in self.skip_tags:
                        self.skip_depth -= 1
                    if tag == "code":
                        self.text_parts.append("`")
                    elif tag == "pre":
                        self.text_parts.append("\n```\n")

                def handle_data(self, data):
                    if self.in_article and self.skip_depth <= 0:
                        self.text_parts.append(data)

            parser = DocExtractor()
            parser.feed(resp.text)
            content = "".join(parser.text_parts).strip()

            if not content:
                # Fallback: extract all text if article detection failed
                class FallbackExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                        self.skip_tags = {"script", "style", "nav"}
                        self.skip_depth = 0

                    def handle_starttag(self, tag, attrs):
                        if tag in self.skip_tags:
                            self.skip_depth += 1

                    def handle_endtag(self, tag):
                        if tag in self.skip_tags:
                            self.skip_depth -= 1

                    def handle_data(self, data):
                        if self.skip_depth <= 0:
                            self.text_parts.append(data)

                fb = FallbackExtractor()
                fb.feed(resp.text)
                content = "".join(fb.text_parts).strip()

            return f"# TQL Documentation: {topic}\nSource: {url}\n\n{content}"

    except Exception as e:
        return f"Error fetching documentation: {e}"


@mcp.tool()
async def run_query(bearer_token: str, app_id: str, query: dict) -> str:
    """Execute a TQL query against TelemetryDeck.

    IMPORTANT: If you haven't read the TQL docs yet in this session, call
    get_tql_docs first to understand the query syntax.

    The query parameter is a full TQL JSON object. TQL supports these query types:
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
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
