import asyncio
import base64

import httpx

BASE_URL = "https://api.telemetrydeckapi.com"


async def login(email: str, password: str) -> dict:
    """Authenticate with TelemetryDeck and return session info including bearer token."""
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        resp = await client.post(
            "/api/v3/users/login",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Length": "0",
            },
        )
        if resp.status_code == 401:
            raise RuntimeError("Login failed (401). Check your email and password.")
        resp.raise_for_status()
        return resp.json()


class TelemetryDeckClient:
    def __init__(self, bearer_token: str, app_id: str):
        self.bearer_token = bearer_token
        self.app_id = app_id
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }

    async def _resolve_data_source(self) -> str:
        """Resolve the correct Druid dataSource for this org.

        Orgs with `useNamespace=true` (the modern default) store signals in a
        per-namespace dataSource named after `org.namespace`. Without setting
        this explicitly, queries hit a near-empty default source and silently
        return zero samples — so we always resolve and inject it.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=15) as client:
            resp = await client.get("/api/v3/organizations/")
            if resp.status_code == 401:
                raise RuntimeError("Authentication failed (401). Check your bearer token.")
            resp.raise_for_status()
            orgs = resp.json()
        if not orgs:
            return "telemetry-signals"
        org = orgs[0]
        settings = org.get("settings") or {}
        if settings.get("useNamespace") and org.get("namespace"):
            return org["namespace"]
        return "telemetry-signals"

    def _scope_query(self, query: dict, data_source: str) -> dict:
        """Inject dataSource and an appID selector filter.

        TelemetryDeck's top-level `appID` field does NOT scope queries against
        namespaced dataSources — you must filter on the `appID` dimension. We
        do this transparently so callers don't have to remember.
        """
        q = dict(query)
        q.setdefault("dataSource", data_source)
        app_filter = {"type": "selector", "dimension": "appID", "value": self.app_id}
        existing = q.get("filter")
        if existing is None:
            q["filter"] = app_filter
        elif isinstance(existing, dict) and existing.get("type") == "and":
            q["filter"] = {"type": "and", "fields": list(existing.get("fields", [])) + [app_filter]}
        else:
            q["filter"] = {"type": "and", "fields": [existing, app_filter]}
        q.pop("appID", None)
        return q

    async def run_query(self, query: dict) -> dict:
        """Submit a TQL query via async endpoint, poll for results."""
        data_source = await self._resolve_data_source()
        query = self._scope_query(query, data_source)
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=30) as client:
            # Submit query
            resp = await client.post("/api/v3/query/calculate-async/", json=query)
            if resp.status_code == 401:
                raise RuntimeError("Authentication failed (401). Check your bearer token.")
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("queryTaskID") or data.get("taskID") or resp.text.strip().strip('"')

            # Poll for completion
            for _ in range(60):
                status_resp = await client.get(f"/api/v3/task/{task_id}/status/")
                status_resp.raise_for_status()
                status_data = status_resp.json()
                status = status_data if isinstance(status_data, str) else status_data.get("status", "")

                if status == "successful":
                    value_resp = await client.get(f"/api/v3/task/{task_id}/value/")
                    value_resp.raise_for_status()
                    return value_resp.json()
                elif status == "failed":
                    # Try to get error details
                    try:
                        value_resp = await client.get(f"/api/v3/task/{task_id}/value/")
                        error_detail = value_resp.text
                    except Exception:
                        error_detail = "No details available"
                    raise RuntimeError(f"Query failed: {error_detail}")

                await asyncio.sleep(1)

            raise RuntimeError(f"Query timed out after 60 seconds (task: {task_id})")

    async def get_insight_query(self, insight_id: str, days_back: int = 30) -> dict:
        """Get the TQL query object for a saved insight."""
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=30) as client:
            resp = await client.post(
                f"/api/v3/insights/{insight_id}/query/",
                json={"daysBack": days_back},
            )
            if resp.status_code == 401:
                raise RuntimeError("Authentication failed (401). Check your bearer token.")
            resp.raise_for_status()
            return resp.json()
