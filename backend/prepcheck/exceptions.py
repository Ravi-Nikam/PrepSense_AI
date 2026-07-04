import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("prepcheck.api")


def structured_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled server error", exc_info=exc)
        return None  # Let Django return its own 500 (DEBUG-aware) handler.

    error_type = exc.__class__.__name__
    req = context.get("request") if context else None
    where = f"{getattr(req, 'method', '?')} {getattr(req, 'path', '?')}"
    level = logging.WARNING if response.status_code < 500 else logging.ERROR
    logger.log(level, "API error %s (%s) on %s", error_type, response.status_code, where)

    # Normalise a few common ones to stable, snake_case type strings.
    known = {
        "ValidationError": "validation_error",
        "NotAuthenticated": "not_authenticated",
        "AuthenticationFailed": "authentication_failed",
        "PermissionDenied": "permission_denied",
        "NotFound": "not_found",
        "Throttled": "throttled",
    }
    response.data = {
        "error": {
            "type": known.get(error_type, "error"),
            "detail": response.data,
            "status": response.status_code,
        }
    }
    return response
