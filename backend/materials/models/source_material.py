from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from materials.constants import IngestionStatus
from tenants.constants import PrepContext
from tenants.managers import TenantScoped


class SourceMaterial(TenantScoped):

    mode = models.CharField(max_length=12, choices=PrepContext.choices, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_materials",
    )

    # Subject (exam) OR role (interview).
    subject_or_role = models.CharField(max_length=150)
    topic = models.CharField(max_length=150, blank=True)

    file = models.FileField(upload_to="materials/", null=True, blank=True)
    source_text = models.TextField(blank=True)

    ingestion_status = models.CharField(
        max_length=12,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
        db_index=True,
    )
    ingestion_error = models.TextField(blank=True)

    class Meta:
        db_table = "source_materials"
        ordering = ("-pk",)

    def __str__(self):
        return f"[{self.mode}] {self.subject_or_role} — {self.topic or 'general'}"

    def clean(self):
        super().clean()
        if self.mode == PrepContext.EXAM and not self.file:
            raise ValidationError({"file": "Exam material requires an uploaded PDF."})
        if self.mode == PrepContext.INTERVIEW and not (self.source_text or self.file):
            raise ValidationError(
                {"source_text": "Interview material requires a job description or role text."}
            )

    @property
    def is_ready(self):
        return self.ingestion_status == IngestionStatus.READY
