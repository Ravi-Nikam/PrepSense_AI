from django.core.cache import cache
from django.utils import timezone
from rest_framework.throttling import BaseThrottle


def _incr(key, ttl):
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:  # key expired between add and incr — treat as fresh
        cache.set(key, 1, ttl)
        return 1


class PerTenantDailyLLMThrottle(BaseThrottle):

    DAY = 60 * 60 * 24
    MONTH = 60 * 60 * 24 * 31

    def allow_request(self, request, view):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            tenant = getattr(request.user, "organization", None)
        if tenant is None:
            return True  # no tenant bound (e.g. unauthenticated) — other layers reject

        now = timezone.now()
        day_cap = getattr(tenant, "llm_daily_call_cap", 0)
        month_cap = getattr(tenant, "llm_monthly_call_cap", 0)
        day_key = f"llmcap:{tenant.id}:d:{now.date().isoformat()}"
        month_key = f"llmcap:{tenant.id}:m:{now.strftime('%Y-%m')}"

        # Read current counts; reject *before* incrementing if either cap is hit.
        if cache.get(day_key, 0) >= day_cap or cache.get(month_key, 0) >= month_cap:
            return False

        _incr(day_key, self.DAY)
        _incr(month_key, self.MONTH)
        return True

    def wait(self):
        return None
