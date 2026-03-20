from __future__ import annotations


class MetaAdsError(Exception):
    error_code = "meta_api_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.details = details or {}


class MetaAuthError(MetaAdsError):
    error_code = "auth_error"


class MetaPermissionError(MetaAdsError):
    error_code = "permission_error"


class MetaRateLimitError(MetaAdsError):
    error_code = "rate_limit_error"


class MetaValidationError(MetaAdsError):
    error_code = "validation_error"


class MetaAPIError(MetaAdsError):
    error_code = "meta_api_error"


def error_from_payload(
    *,
    message: str,
    status_code: int | None = None,
    request_id: str | None = None,
    details: dict | None = None,
) -> MetaAdsError:
    return MetaAPIError(message, status_code=status_code, request_id=request_id, details=details)

