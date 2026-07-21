"""
Minimal async client for Cloudflare D1's HTTP query API.

D1 is normally queried from inside a Cloudflare Worker via the `env.DB` binding,
but it also exposes a REST endpoint that lets any external service (like this
FastAPI app) run SQL against it directly:

    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query

Docs: https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database
"""

import json
import os
from typing import Any

import httpx

CF_ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
CF_D1_DATABASE_ID = os.environ["CF_D1_DATABASE_ID"]
CF_API_TOKEN = os.environ["CF_API_TOKEN"]

D1_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/d1/database/{CF_D1_DATABASE_ID}/query"
)

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}


class D1Error(Exception):
    """Raised when D1 returns success=false or the HTTP call itself fails."""


async def d1_query(sql: str, params: list[Any] | None = None) -> list[dict]:
    """
    Run a single SQL statement against D1 and return the result rows.

    Use `?` placeholders in `sql` and pass values positionally in `params` —
    never interpolate user input into the SQL string directly.
    """
    payload = {"sql": sql, "params": params or []}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(D1_URL, headers=HEADERS, json=payload)

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise D1Error(f"D1 returned a non-JSON response ({resp.status_code}): {resp.text[:300]}") from exc

    if resp.status_code != 200 or not data.get("success"):
        raise D1Error(json.dumps(data.get("errors") or data))

    # The API wraps results per-statement; we only ever send one statement.
    result = data["result"][0]
    return result.get("results", [])


async def d1_execute(sql: str, params: list[Any] | None = None) -> None:
    """Run a statement (INSERT/UPDATE/DELETE) where we don't need the rows back."""
    await d1_query(sql, params)
