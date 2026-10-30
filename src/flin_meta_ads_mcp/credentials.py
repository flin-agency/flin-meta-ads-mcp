from __future__ import annotations

import json
import math
import os
import tempfile
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Credentials:
    app_id: str
    app_secret: str = field(repr=False)
    access_token: str = field(repr=False)
    api_version: str
    expires_at: float | None = None


def credentials_path(env: Mapping[str, str]) -> Path:
    custom = env.get("META_AUTH_FILE", "").strip()
    return Path(custom).expanduser() if custom else (
        Path.home() / ".config" / "flin-meta-ads-mcp" / "credentials.json"
    )


def load_credentials(path: Path) -> Credentials | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise ValueError("Cannot read saved login. Run flin-meta-ads-mcp login again.") from None
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key].strip()
        for key in ("app_id", "app_secret", "access_token", "api_version")
    ):
        raise ValueError("Invalid saved login. Run flin-meta-ads-mcp login again.")
    expires_at = data.get("expires_at")
    if expires_at is not None:
        if (
            isinstance(expires_at, bool)
            or not isinstance(expires_at, (int, float))
            or not math.isfinite(expires_at)
        ):
            raise ValueError("Invalid login expiration. Run flin-meta-ads-mcp login again.")
        if expires_at <= time.time():
            raise ValueError("Saved login expired. Run flin-meta-ads-mcp login again.")
    return Credentials(
        app_id=data["app_id"], app_secret=data["app_secret"],
        access_token=data["access_token"], api_version=data["api_version"],
        expires_at=expires_at,
    )


def save_credentials(path: Path, credentials: Credentials) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".login-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(credentials), stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
