from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

import httpx

from .config import validate_connection_settings
from .errors import (
    MetaAdsError,
    MetaAPIError,
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
        app_secret: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        validate_connection_settings(api_version, timeout_seconds, max_retries)
        self.access_token = access_token
        self._app_secret = app_secret
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = client is None
        self.last_request_id: str | None = None
        self._default_ad_account_id: str | None = None
        self._resolved_ad_account_id: str | None = None

    def __enter__(self) -> Self:
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

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> _RequestResult:
        if method != "GET" or json_body is not None:
            raise PermissionError("Meta Ads API requests are restricted to GET")
        url = self._build_url(path)
        request_params = dict(params or {})
        for key in ("access_token", "appsecret_proof", "app_secret", "client_secret"):
            request_params.pop(key, None)
        if any(key.lower() in {"method", "http_method", "x-http-method-override"} for key in request_params):
            raise PermissionError("HTTP method overrides are not allowed")
        if self._app_secret:
            request_params["appsecret_proof"] = hmac.new(
                self._app_secret.encode("utf-8"),
                self.access_token.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        request_headers = {"Authorization": f"Bearer {self.access_token}"}
        attempts = 0

        while True:
            try:
                response = self._client_or_new().request(
                    method, url, params=request_params, headers=request_headers,
                    follow_redirects=False,
                )
            except httpx.HTTPError:
                raise MetaAPIError("Could not contact Meta. Retry the request.") from None
            request_id = self._request_id_from_response(response)
            if 200 <= response.status_code < 300:
                try:
                    payload = response.json() if response.content else {}
                except ValueError:
                    raise MetaAPIError("Meta returned an invalid JSON response") from None
                if not isinstance(payload, dict):
                    raise MetaAPIError("Meta returned an invalid response")
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
        if not re.fullmatch(
            r"(?:me(?:/(?:adaccounts|permissions))?|[0-9]+(?:/(?:previews))?|"
            r"act_[0-9]+(?:/(?:campaigns|adsets|ads|adimages|adcreatives|insights|generatepreviews))?|"
            r"generatepreviews)", path
        ):
            raise ValueError("Unsupported Meta read endpoint")
        return f"https://graph.facebook.com/{self.api_version}/{path}"

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
        error = error if isinstance(error, dict) else {}
        # Upstream messages, error_data and HTML can echo tokens and signed URLs.
        message = "Meta API request failed. Check permissions and request parameters."
        safe_error = {
            key: value for key in ("code", "error_subcode", "is_transient")
            if isinstance((value := error.get(key)), (int, bool))
        }
        code = error.get("code")

        details = {
            "status_code": response.status_code,
            "error": safe_error,
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
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}
