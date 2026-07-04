import pytest
from django.core.management import call_command

from accounts.constants import Role
from accounts.models import User
from attempts.models import Attempt
from questions.models import Question
from tenants.constants import OrganizationType
from tenants.context import tenant_context
from tenants.models import Organization

pytestmark = pytest.mark.django_db


def test_seed_creates_both_modes_with_content():
    call_command("seed_demo")

    assert Organization.objects.filter(type=OrganizationType.SCHOOL).count() == 2
    assert Organization.objects.filter(
        type__in=[OrganizationType.COMPANY, OrganizationType.INSTITUTE]
    ).count() == 2

    # Roles across both modes exist.
    assert User.objects.filter(role=Role.TEACHER).exists()
    assert User.objects.filter(role=Role.MENTOR).exists()
    assert User.objects.filter(role=Role.PARENT, linked_learner__isnull=False).exists()

    # Questions and graded attempts were produced (offline).
    assert Question.all_objects.exists()
    assert Attempt.all_objects.filter(score__isnull=False).exists()


def test_seeded_data_is_tenant_isolated():
    call_command("seed_demo")
    school_a = Organization.objects.get(name="Springfield High")
    school_b = Organization.objects.get(name="Riverdale High")

    with tenant_context(school_a):
        a_count = Attempt.objects.count()
    with tenant_context(school_b):
        b_count = Attempt.objects.count()

    total = Attempt.all_objects.count()
    assert a_count > 0 and b_count > 0
    # Each tenant sees only its slice, never the whole set.
    assert a_count < total and b_count < total


def test_seed_is_idempotent():
    call_command("seed_demo")
    orgs = Organization.objects.count()
    users = User.objects.count()
    call_command("seed_demo")  # re-run wipes + recreates
    assert Organization.objects.count() == orgs
    assert User.objects.count() == users
