"""
Rate limiting via SlowAPI (in-process token bucket).

This is intentionally simple — in production with multiple workers you'd
back this with Redis. For an internal-scale app and CI environments,
in-process is sufficient AND has zero external dependencies.

Tests can short-circuit limiting by setting RATE_LIMIT_DISABLED=1.
"""

import os
from slowapi import Limiter
from slowapi.util import get_remote_address


def _key_func(request) -> str:
    """Per-IP keying. Honors X-Forwarded-For when behind a reverse proxy."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


# A globally-disabled limiter is what we hand to tests so they can hammer
# the API without hitting throttles.
_DISABLED = os.getenv("RATE_LIMIT_DISABLED") == "1"

limiter = Limiter(
    key_func=_key_func,
    enabled=not _DISABLED,
    # Quiet headers so non-throttled responses don't carry noise.
    headers_enabled=False,
)
