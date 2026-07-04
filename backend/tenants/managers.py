import logging

from django.conf import settings
from django.db import models

from .context import get_current_tenant

logger = logging.getLogger("prepcheck.tenants")


class TenantScopedQuerySet(models.QuerySet):

    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        # No tenant bound. Fail closed unless explicitly relaxed.
        if getattr(settings, "TENANT_STRICT", True):
            return qs.none()
        return qs

    # --- explicit escape hatches (bypass the ambient scoping) ---
    def unscoped(self):
        return super().get_queryset()

    def for_tenant(self, tenant):
        return super().get_queryset().filter(tenant=tenant)


class TenantScoped(models.Model):

    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="+",  # no reverse accessor; avoids clashes across many models
        db_index=True,
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()       # scoped: the default everyone uses
    all_objects = models.Manager()        # unscoped: for internal/admin use

    class Meta:
        abstract = True
        base_manager_name = "all_objects"  # see decision #3 above

    def save(self, *args, **kwargs):
        if self.tenant_id is None:
            tenant = get_current_tenant()
            if tenant is not None:
                self.tenant = tenant
        if self.tenant_id is None:
            raise ValueError(
                f"Refusing to save {type(self).__name__} with no tenant bound. "
                "Set one via middleware, tenant_context(), or for_tenant()."
            )
        super().save(*args, **kwargs)
