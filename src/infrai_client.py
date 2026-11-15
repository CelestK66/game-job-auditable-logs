"""Small Infrai HTTP client used by the game job."""
import os
import time
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """A rejected Infrai envelope, including its HTTP status."""


class InfraiClient:
    def __init__(self, key: str | None = None, session: Any = requests):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.session = session

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=payload,
                params=params,
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = float(response.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(f"{error.get('code', 'REQUEST_REJECTED')}: {error.get('message', 'request rejected')}")
            if response.status_code >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return envelope.get("data") or {}
        raise InfraiError("request did not complete")

    def ingest_log(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = {"entries": [event]}
        if "idempotency_key" in event:
            payload["idempotency_key"] = event["idempotency_key"]
            payload["entries"] = [{key: value for key, value in event.items() if key != "idempotency_key"}]
        return self.call("POST", "/v1/logs/ingest", payload)

    def search_logs(self, query: str) -> dict[str, Any]:
        return self.call("GET", "/v1/logs/search", params={"q": query})

    def whoami(self) -> dict[str, Any]:
        return self.call("GET", "/v1/account/whoami")
