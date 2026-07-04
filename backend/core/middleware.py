import logging
import time
import uuid

from core.log_context import reset_request_id, set_request_id

logger = logging.getLogger("prepcheck.request")

# Noisy, low-value paths kept out of the access log.
SKIP_PREFIXES = ("/healthz", "/static/", "/favicon")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_request_id(uuid.uuid4().hex[:8])
        start = time.monotonic()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            if not request.path.startswith(SKIP_PREFIXES):
                duration_ms = (time.monotonic() - start) * 1000.0
                status = getattr(response, "status_code", 500)
                level = (
                    logging.INFO if status < 400
                    else logging.WARNING if status < 500
                    else logging.ERROR
                )
                tenant = getattr(request, "tenant", None)
                logger.log(
                    level,
                    "%s %s -> %s (%.0fms)",
                    request.method, request.path, status, duration_ms,
                    extra={
                        "tenant": getattr(tenant, "id", None),
                        "user": getattr(request, "jwt_user_id", None),
                    },
                )
            reset_request_id(token)
