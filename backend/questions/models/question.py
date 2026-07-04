from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.fields import VectorField
from questions.constants import Difficulty, QuestionCategory
from tenants.constants import PrepContext
from tenants.managers import TenantScoped


class Question(TenantScoped):

    source_material = models.ForeignKey(
        "materials.SourceMaterial",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    source_chunk = models.ForeignKey(
        "materials.MaterialChunk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )

    mode = models.CharField(max_length=12, choices=PrepContext.choices, db_index=True)
    topic_or_category = models.CharField(max_length=150)

    difficulty = models.CharField(
        max_length=8, choices=Difficulty.choices, null=True, blank=True
    )  # exam only
    category = models.CharField(
        max_length=12, choices=QuestionCategory.choices, null=True, blank=True
    )  # interview only

    question_text = models.TextField()
    reference_answer = models.TextField(blank=True)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)

    class Meta:
        db_table = "questions"
        ordering = ("-pk",)

    def __str__(self):
        return self.question_text[:60]

    def clean(self):
        super().clean()
        if self.mode == PrepContext.EXAM:
            if not self.difficulty:
                raise ValidationError({"difficulty": "Exam questions require a difficulty."})
            if self.category:
                raise ValidationError({"category": "Exam questions must not set an interview category."})
        elif self.mode == PrepContext.INTERVIEW:
            if not self.category:
                raise ValidationError({"category": "Interview questions require a category."})
            if self.difficulty:
                raise ValidationError({"difficulty": "Interview questions must not set an exam difficulty."})
