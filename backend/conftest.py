import pytest

from accounts.constants import Role
from accounts.models import User
from tenants.constants import OrganizationType
from tenants.context import clear_current_tenant
from tenants.models import Organization


@pytest.fixture(autouse=True)
def _reset_tenant_context():
    from django.core.cache import cache

    clear_current_tenant()
    cache.clear()
    yield
    clear_current_tenant()
    cache.clear()


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Springfield High", type=OrganizationType.SCHOOL)


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Acme Corp", type=OrganizationType.COMPANY)


@pytest.fixture
def make_user(db):

    def _make(org, role=Role.STUDENT, email=None, password="Passw0rd!123", **extra):
        email = email or f"{role.lower()}-{org.id}-{User.objects.count()}@example.com"
        return User.objects.create_user(
            email=email,
            password=password,
            organization=org,
            role=role,
            **extra,
        )

    return _make


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def make_material(db):

    def _make(org, uploaded_by=None, mode=None, **extra):
        from materials.models import SourceMaterial
        from tenants.constants import PrepContext
        from tenants.context import tenant_context

        mode = mode or PrepContext.INTERVIEW
        defaults = {
            "mode": mode,
            "subject_or_role": "Backend Engineer",
            "source_text": "We need a backend engineer skilled in Django and Postgres.",
            "uploaded_by": uploaded_by,
        }
        defaults.update(extra)
        with tenant_context(org):
            return SourceMaterial.objects.create(**defaults)

    return _make


@pytest.fixture
def make_question(db):

    def _make(org, material, **extra):
        from questions.constants import QuestionCategory
        from questions.models import Question
        from tenants.constants import PrepContext
        from tenants.context import tenant_context

        defaults = {
            "source_material": material,
            "mode": material.mode,
            "topic_or_category": "system design",
            "question_text": "How would you design a rate limiter?",
            "reference_answer": "Token bucket / sliding window; per-tenant keys.",
        }
        if material.mode == PrepContext.INTERVIEW:
            defaults["category"] = QuestionCategory.TECHNICAL
        defaults.update(extra)
        with tenant_context(org):
            return Question.objects.create(**defaults)

    return _make


@pytest.fixture
def auth_client(db):

    def _auth(user, password="Passw0rd!123"):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        token = RefreshToken.for_user(user)
        token["tenant_id"] = user.organization_id
        token["role"] = user.role
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client

    return _auth
