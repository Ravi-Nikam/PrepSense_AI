from django.db import models


class Role(models.TextChoices):
    ORG_ADMIN = "ORG_ADMIN", "Organisation admin"
    # Exam mode
    TEACHER = "TEACHER", "Teacher"
    PARENT = "PARENT", "Parent"
    STUDENT = "STUDENT", "Student"
    # Interview mode
    MENTOR = "MENTOR", "Mentor / coach"
    CANDIDATE = "CANDIDATE", "Candidate"

    @classmethod
    def observer_roles(cls):
        return {cls.ORG_ADMIN, cls.TEACHER, cls.PARENT, cls.MENTOR}

    @classmethod
    def learner_roles(cls):
        return {cls.STUDENT, cls.CANDIDATE}
