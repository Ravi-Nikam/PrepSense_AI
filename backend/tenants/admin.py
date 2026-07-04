from django.contrib import admin

from tenants.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "type", "is_active",
        "llm_daily_call_cap", "llm_monthly_call_cap", "created_at",
    )
    list_filter = ("type", "is_active")
    search_fields = ("name", "email", "city")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)
