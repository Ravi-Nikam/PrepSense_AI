import logging

from .context import clear_current_tenant, set_current_tenant

logger = logging.getLogger("prepcheck.tenants")


class CurrentTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from core.log_context import reset_user_id, set_user_id

        token = None
        tenant = self._resolve_tenant(request)
        if tenant is not None:
            token = set_current_tenant(tenant)
        # Expose it on the request too, for convenience in views/serializers.
        request.tenant = tenant
        user_token = set_user_id(getattr(request, "jwt_user_id", None))
        try:
            return self.get_response(request)
        finally:
            clear_current_tenant(token)
            reset_user_id(user_token)

    def _resolve_tenant(self, request):
        # Import here to avoid loading DRF/simplejwt at settings-import time.
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import (
            AuthenticationFailed,
            InvalidToken,
            TokenError,
        )

        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.lower().startswith("bearer "):
            return None

        authenticator = JWTAuthentication()
        try:
            raw = authenticator.get_raw_token(header.encode())
            validated = authenticator.get_validated_token(raw)
            user = authenticator.get_user(validated)
        except (InvalidToken, TokenError, AuthenticationFailed):
            # Malformed/expired token — leave unbound; DRF returns 401 downstream.
            return None

        # Stash the resolved user id for the access log / logging context.
        request.jwt_user_id = getattr(user, "id", None)

        claimed_tenant_id = validated.get("tenant_id")
        user_tenant_id = getattr(user, "organization_id", None)

        if user_tenant_id is None:
            logger.warning(
                "Authenticated user has no organization; refusing to bind tenant.",
                extra={"user": getattr(user, "id", None), "tenant": None},
            )
            return None

        # Defence in depth: the token's tenant claim MUST match the user's org.
        if claimed_tenant_id is not None and str(claimed_tenant_id) != str(user_tenant_id):
            logger.warning(
                "JWT tenant_id claim (%s) does not match user's organization (%s); "
                "refusing to bind tenant.",
                claimed_tenant_id,
                user_tenant_id,
                extra={"user": getattr(user, "id", None), "tenant": user_tenant_id},
            )
            return None

        # Resolve to the actual Organization instance (unscoped: no tenant bound yet).
        from .models import Organization

        return Organization.objects.filter(id=user_tenant_id).first()
