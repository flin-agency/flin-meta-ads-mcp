from __future__ import annotations

from typing import Any


def ok_response(
    *,
    data: Any,
    next_after: str | None,
    has_next: bool,
    api_version: str,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "paging": {
            "next_after": next_after,
            "has_next": has_next,
        },
        "meta": {
            "api_version": api_version,
            "request_id": request_id,
        },
    }


def error_response(
    *,
    code: str,
    message: str,
    api_version: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "paging": {
            "next_after": None,
            "has_next": False,
        },
        "meta": {
            "api_version": api_version,
            "request_id": request_id,
        },
    }

