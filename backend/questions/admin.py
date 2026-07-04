from django.contrib import admin

from core.admin_mixins import UnscopedTenantAdmin
from questions.models import Question


@admin.register(Question)
class QuestionAdmin(UnscopedTenantAdmin, admin.ModelAdmin):
    list_display = (
        "id", "short_question", "topic_or_category", "mode",
        "difficulty", "category", "source_material", "tenant",
    )
    list_filter = ("mode", "difficulty", "category", "tenant")
    search_fields = ("question_text", "topic_or_category")
    exclude = ("embedding",)  # large vector
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="question")
    def short_question(self, obj):
        return (obj.question_text or "")[:60]
