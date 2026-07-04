from django.contrib import admin

from core.admin_mixins import UnscopedTenantAdmin
from materials.models import MaterialChunk, SourceMaterial


@admin.register(SourceMaterial)
class SourceMaterialAdmin(UnscopedTenantAdmin, admin.ModelAdmin):
    list_display = (
        "id", "subject_or_role", "topic", "mode", "ingestion_status",
        "tenant", "uploaded_by", "created_at",
    )
    list_filter = ("mode", "ingestion_status", "tenant")
    search_fields = ("subject_or_role", "topic")
    readonly_fields = ("created_at", "updated_at", "ingestion_status", "ingestion_error")


@admin.register(MaterialChunk)
class MaterialChunkAdmin(UnscopedTenantAdmin, admin.ModelAdmin):
    list_display = ("id", "source_material", "chunk_index", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("chunk_text",)
    exclude = ("embedding",)  # large vector; not useful in the admin form
    readonly_fields = ("created_at", "updated_at")
