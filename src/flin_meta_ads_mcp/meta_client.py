from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping

import httpx

from .errors import (
    MetaAPIError,
    MetaAdsError,
    MetaAuthError,
    MetaPermissionError,
    MetaRateLimitError,
    MetaValidationError,
)


@dataclass(slots=True)
class _RequestResult:
    payload: dict[str, Any]
    request_id: str | None


class MetaClient:
    def __init__(
        self,
        *,
        access_token: str,
        api_version: str,
        timeout_seconds: float,
        max_retries: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.access_token = access_token
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = client is None
        self.last_request_id: str | None = None

    def __enter__(self) -> "MetaClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_json(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        result = self.request_json("GET", path, params=params)
        self.last_request_id = result.request_id
        return result.payload

    def post_json(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.request_json("POST", path, params=params, json_body=json_body)
        self.last_request_id = result.request_id
        return result.payload

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> _RequestResult:
        url = self._build_url(path)
        request_params = dict(params or {})
        request_params.pop("access_token", None)
        request_headers = {"Authorization": f"Bearer {self.access_token}"}
        attempts = 0

        while True:
            response = self._client_or_new().request(
                method,
                url,
                params=request_params,
                headers=request_headers,
                json=dict(json_body or {}) if json_body is not None else None,
            )
            request_id = self._request_id_from_response(response)
            if response.status_code < 400:
                payload = response.json() if response.content else {}
                return _RequestResult(payload=payload, request_id=request_id)

            error = self._error_from_response(response, request_id=request_id)
            if self._should_retry(response.status_code) and attempts < self.max_retries:
                time.sleep(self._backoff_seconds(attempts))
                attempts += 1
                continue
            raise error

    def _client_or_new(self) -> httpx.Client:
        return self._client

    def _build_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return f"https://graph.facebook.com/{self.api_version}/{clean_path}"

    @staticmethod
    def _request_id_from_response(response: httpx.Response) -> str | None:
        return response.headers.get("x-fb-request-id") or response.headers.get("x-fb-trace-id")

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code < 600

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return min(2.0**attempt * 0.5, 8.0)

    def _error_from_response(self, response: httpx.Response, *, request_id: str | None) -> MetaAdsError:
        payload = _safe_json(response)
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = error.get("message") or response.text or "Meta API request failed"
        code = error.get("code")

        details = {
            "status_code": response.status_code,
            "error": error,
        }

        if response.status_code in {401, 403} or code in {190, 102}:
            if response.status_code == 401 or code == 190:
                return MetaAuthError(message, status_code=response.status_code, request_id=request_id, details=details)
            return MetaPermissionError(
                message,
                status_code=response.status_code,
                request_id=request_id,
                details=details,
            )

        if response.status_code == 429:
            return MetaRateLimitError(
                message,
                status_code=response.status_code,
                request_id=request_id,
                details=details,
            )

        if response.status_code == 400 or code in {100, 1000, 2500, 2635}:
            return MetaValidationError(
                message,
                status_code=response.status_code,
                request_id=request_id,
                details=details,
            )

        return MetaAPIError(message, status_code=response.status_code, request_id=request_id, details=details)


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
