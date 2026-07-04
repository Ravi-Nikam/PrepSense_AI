from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.constants import Role


class CustomUserManager(BaseUserManager):

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        org = extra_fields.pop("organization", None)
        user = self.model(email=email, **extra_fields)
        if org is not None:
            if isinstance(org, (int, str)):
                user.organization_id = int(org)
            else:
                user.organization = org
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ORG_ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="users",
        db_index=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)

    linked_learner = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="observers",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["organization", "role"]

    class Meta:
        db_table = "users"
        ordering = ("pk",)

    def __str__(self):
        return f"{self.email} [{self.role}]"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)
