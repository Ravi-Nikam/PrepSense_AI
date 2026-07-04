from django.db import models


class Difficulty(models.TextChoices):

    EASY = "EASY", "Easy"
    MEDIUM = "MEDIUM", "Medium"
    HARD = "HARD", "Hard"


class QuestionCategory(models.TextChoices):

    BEHAVIORAL = "BEHAVIORAL", "Behavioral"
    TECHNICAL = "TECHNICAL", "Technical"
