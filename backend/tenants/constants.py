from django.db import models


class OrganizationType(models.TextChoices):

    SCHOOL = "SCHOOL", "School (exam prep)"
    COMPANY = "COMPANY", "Company (interview prep)"
    INSTITUTE = "INSTITUTE", "Coaching institute (interview prep)"
    INDIVIDUAL = "INDIVIDUAL", "Individual self-serve account"


class PrepContext(models.TextChoices):

    EXAM = "EXAM", "Exam preparation"
    INTERVIEW = "INTERVIEW", "Interview preparation"
