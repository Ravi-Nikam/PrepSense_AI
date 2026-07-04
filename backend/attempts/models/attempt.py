from django.conf import settings
from django.db import models

from tenants.managers import TenantScoped


class Attempt(TenantScoped):

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    submitted_answer = models.TextField()

    # Set by grading. 0–100 scale.
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attempts"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["learner", "question"]),
        ]

    def __str__(self):
        return f"attempt#{self.pk} learner={self.learner_id} q={self.question_id}"

    @property
    def is_graded(self):
        return self.score is not None
