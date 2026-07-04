import logging
import time

logger = logging.getLogger("prepcheck.llm")

# HTTP statuses worth retrying (rate limit, conflict, timeouts, server errors).
TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# Substrings that mark a transient provider error when no status code is exposed.
TRANSIENT_MARKERS = (
    "resource_exhausted", "rate limit", "rate_limit", "ratelimit", "too many requests",
    "overloaded", "temporarily", "timed out", "timeout", "unavailable",
    "connection", "try again", "internal error", "internal server",
)


def is_transient(exc):
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(code, int) and code in TRANSIENT_STATUS:
        return True
    name = type(exc).__name__.lower()
    if any(k in name for k in ("timeout", "connection", "unavailable", "ratelimit",
                               "overloaded", "resourceexhausted", "toomanyrequests",
                               "apiconnection", "serviceunavailable", "internalserver")):
        return True
    msg = str(exc).lower()
    return any(k in msg for k in TRANSIENT_MARKERS)


def retry_call(fn, *, attempts=3, base_delay=0.6, max_delay=8.0, label="provider",
               sleep=time.sleep):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — deliberately broad; we re-raise
            last = exc
            if i == attempts - 1 or not is_transient(exc):
                raise
            delay = min(max_delay, base_delay * (2 ** i))
            logger.warning(
                "Transient %s error (attempt %s/%s): %s: %s — retrying in %.1fs",
                label, i + 1, attempts, type(exc).__name__, exc, delay,
            )
            sleep(delay)
    raise last  # pragma: no cover — loop always returns or raises
