import logging

from .context import get_current_tenant


class TenantContextFilter(logging.Filter):
    def filter(self, record):
        from core.log_context import get_request_id, get_user_id

        if not hasattr(record, "tenant"):
            tenant = get_current_tenant()
            record.tenant = getattr(tenant, "id", None) if tenant else None
        if not hasattr(record, "user"):
            record.user = get_user_id()
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True
