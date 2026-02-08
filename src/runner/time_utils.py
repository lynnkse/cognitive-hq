"""Time utilities — consistent timestamp generation.

All timestamps use ISO 8601 UTC format.
"""

from datetime import datetime, timezone


def utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
