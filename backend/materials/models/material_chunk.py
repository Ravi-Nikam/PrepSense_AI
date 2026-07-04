from django.conf import settings
from django.db import models

from core.fields import VectorField
from tenants.managers import TenantScoped


class MaterialChunk(TenantScoped):

    source_material = models.ForeignKey(
        "materials.SourceMaterial",
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)

    class Meta:
        db_table = "material_chunks"
        ordering = ("source_material_id", "chunk_index")
        constraints = [
            models.UniqueConstraint(
                fields=["source_material", "chunk_index"],
                name="uniq_chunk_index_per_material",
            )
        ]

    def __str__(self):
        return f"{self.source_material_id}#{self.chunk_index}"
