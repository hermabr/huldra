"""
Furu Dashboard: A web-based monitoring interface for Furu experiments.

Install with: uv add furu[dashboard]
Run with: furu-dashboard serve
"""

from importlib import metadata


def _resolve_version() -> str:
    try:
        return metadata.version("furu")
    except metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _resolve_version()
