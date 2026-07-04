import pytest

from accounts.constants import Role
from accounts.models import User
from tenants.models import Organization

pytestmark = pytest.mark.django_db


def _make_superadmin(org, make_user):
    return make_user(
        org, role=Role.ORG_ADMIN, email="root@platform.local",
        is_superuser=True, is_staff=True,
    )


def test_org_admin_cannot_create_organization(org_a, make_user, auth_client):
    admin = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")
    resp = auth_client(admin).post(
        "/api/organizations/", {"name": "Sneaky", "type": "SCHOOL"}, format="json"
    )
    assert resp.status_code == 403
    assert not Organization.objects.filter(name="Sneaky").exists()


def test_unauthenticated_is_401(api_client):
    assert api_client.get("/api/organizations/").status_code == 401


def test_superuser_creates_org_with_first_admin(org_a, make_user, auth_client):
    superadmin = _make_superadmin(org_a, make_user)
    resp = auth_client(superadmin).post(
        "/api/organizations/",
        {
            "name": "New School",
            "type": "SCHOOL",
            "city": "Pune",
            "admin_email": "principal@newschool.local",
            "admin_password": "Str0ng@Pass1",
        },
        format="json",
    )
    assert resp.status_code == 201
    org = Organization.objects.get(name="New School", city="Pune")
    admin = User.objects.get(email="principal@newschool.local")
    # The admin lands in the brand-new org with the ORG_ADMIN role.
    assert admin.organization_id == org.id
    assert admin.role == Role.ORG_ADMIN


def test_org_creation_requires_admin_credentials(org_a, make_user, auth_client):
    superadmin = _make_superadmin(org_a, make_user)
    resp = auth_client(superadmin).post(
        "/api/organizations/", {"name": "No Admin", "type": "SCHOOL"}, format="json"
    )
    assert resp.status_code == 400
    # No orphan org when the admin details are missing.
    assert not Organization.objects.filter(name="No Admin").exists()


def test_duplicate_admin_email_rolls_back_org(org_a, make_user, auth_client):
    superadmin = _make_superadmin(org_a, make_user)
    make_user(org_a, role=Role.TEACHER, email="taken@x.com")
    resp = auth_client(superadmin).post(
        "/api/organizations/",
        {
            "name": "Rollback School",
            "type": "SCHOOL",
            "admin_email": "taken@x.com",
            "admin_password": "Str0ng@Pass1",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert not Organization.objects.filter(name="Rollback School").exists()


def test_superuser_lists_all_tenants(org_a, org_b, make_user, auth_client):
    superadmin = make_user(
        org_a, role=Role.ORG_ADMIN, email="root@platform.local",
        is_superuser=True, is_staff=True,
    )
    resp = auth_client(superadmin).get("/api/organizations/")
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()["results"]}
    # Sees BOTH tenants — not confined to its own org like an ORG_ADMIN.
    assert {"Springfield High", "Acme Corp"} <= names
