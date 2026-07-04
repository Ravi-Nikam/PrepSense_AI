from django.conf import settings
from django.db import models
from django.utils import timezone

from tenants.constants import OrganizationType


class Organization(models.Model):

    name = models.CharField(max_length=150)
    type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        db_index=True,
    )

    # Contact / profile (optional).
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=80, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    llm_daily_call_cap = models.PositiveIntegerField(
        default=settings.LLM_DAILY_CALL_CAP_PER_TENANT
    )
    llm_monthly_call_cap = models.PositiveIntegerField(
        default=settings.LLM_MONTHLY_CALL_CAP_PER_TENANT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="organization_created_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="organization_updated_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "organizations"
        ordering = ("pk",)

    def __str__(self):
        return f"{self.name} ({self.type})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)
