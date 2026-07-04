from django.contrib import admin

from attempts.models import Attempt
from core.admin_mixins import UnscopedTenantAdmin


@admin.register(Attempt)
class AttemptAdmin(UnscopedTenantAdmin, admin.ModelAdmin):
    list_display = ("id", "learner", "question", "score", "graded_at", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("submitted_answer", "feedback")
    readonly_fields = ("created_at", "updated_at", "graded_at")
