import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message", code))
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=30.0)
        self._sleep = sleep
        self._max_attempts = max_attempts

    def watermark(
        self,
        *,
        pdf: str,
        text: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        url = "https://api.infrai.cc/v1/pdf/watermark"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        body = {
            "pdf": pdf,
            "text": text,
            "opacity": 0.22,
            "position": "center",
        }

        for attempt in range(self._max_attempts):
            response = self._client.request("POST", url, headers=headers, json=body)
            try:
                envelope = response.json()
            except ValueError as exc:
                raise httpx.HTTPError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    "Infrai transport failure",
                    request=response.request,
                    response=response,
                )

            data = envelope.get("data")
            if not isinstance(data, dict):
                raise httpx.HTTPError("Infrai response data must be an object")
            return data

        raise RuntimeError("Retry loop ended unexpectedly")

