from django.contrib.auth.password_validation import validate_password

from accounts.models import User


def create_user(*, organization, password, **fields):
    user = User(organization=organization, **fields)
    user.set_password(password)
    user.save()
    return user


def set_user_password(user, raw_password):
    validate_password(raw_password, user=user)
    user.set_password(raw_password)
    user.save(update_fields=["password", "updated_at"])


def deactivate_user(user):
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
