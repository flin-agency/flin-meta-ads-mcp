from __future__ import annotations

try:
    from importlib.metadata import version
except ImportError:  # pragma: no cover - Python < 3.8 is unsupported anyway.
    version = None  # type: ignore[assignment]

__all__ = ["__version__"]

if version is None:
    __version__ = "0.0.0"
else:
    try:
        __version__ = version("flin-meta-ads-mcp")
    except Exception:
        __version__ = "0.0.0"

