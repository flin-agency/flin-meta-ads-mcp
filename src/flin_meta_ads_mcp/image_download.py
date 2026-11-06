from __future__ import annotations

from urllib.parse import urljoin, urlsplit

import httpx

from .errors import MetaAPIError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp",
}


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or not any(host.endswith("." + domain) for domain in ("fbcdn.net", "fbsbx.com"))
    ):
        raise ValueError("Image URL must be an HTTPS Meta CDN URL (fbcdn.net or fbsbx.com)")


def _matches_format(data: bytes, mime_type: str) -> bool:
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    return data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def download_image(url: str, *, timeout_seconds: float) -> tuple[bytes, str]:
    """Fetch signed CDN URLs without Graph credentials or automatic redirects."""
    _validate_url(url)
    try:
        # Separate client: never inherit Graph Authorization, cookies, or auth hooks.
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            for hop in range(MAX_REDIRECTS + 1):
                _validate_url(url)
                with client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location or hop == MAX_REDIRECTS:
                            raise ValueError("Image download exceeded redirect limit or has no destination")
                        url = urljoin(url, location)
                        continue
                    if response.status_code != 200:
                        raise MetaAPIError(
                            "Image download failed; fetch a fresh image URL from Meta and retry",
                            status_code=response.status_code,
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ValueError("Compressed image transfer is not supported")
                    mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if mime_type not in IMAGE_EXTENSIONS:
                        raise ValueError("Image must be JPEG, PNG, GIF, or WebP")
                    length = response.headers.get("content-length")
                    if length is not None and int(length) > MAX_IMAGE_BYTES:
                        raise ValueError("Image exceeds the 5 MiB download limit")
                    data = bytearray()
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):
                        if len(data) + len(chunk) > MAX_IMAGE_BYTES:
                            raise ValueError("Image exceeds the 5 MiB download limit")
                        data.extend(chunk)
                    content = bytes(data)
                    if not _matches_format(content, mime_type):
                        raise ValueError("Image content does not match its declared format")
                    return content, mime_type
    except httpx.HTTPError as exc:
        # Do not expose signed URLs or response bodies through error messages.
        raise MetaAPIError("Image download failed; fetch a fresh image URL from Meta and retry") from exc
    raise ValueError("Image download exceeded redirect limit")
