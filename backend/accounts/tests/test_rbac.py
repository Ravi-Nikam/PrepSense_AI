import pytest

from accounts.constants import Role
from accounts.models import User

pytestmark = pytest.mark.django_db


def test_non_admin_cannot_access_user_management(org_a, make_user, auth_client):
    student = make_user(org_a, role=Role.STUDENT, email="stu@a.com")
    resp = auth_client(student).get("/api/users/")
    assert resp.status_code == 403


def test_unauthenticated_is_401(api_client):
    assert api_client.get("/api/users/").status_code == 401


def test_admin_lists_only_own_tenant_users(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")
    make_user(org_a, role=Role.STUDENT, email="stu@a.com")
    make_user(org_b, role=Role.STUDENT, email="stu@b.com")  # other tenant

    resp = auth_client(admin_a).get("/api/users/")
    assert resp.status_code == 200
    emails = {row["email"] for row in resp.json()["results"]}
    assert emails == {"admin@a.com", "stu@a.com"}
    assert "stu@b.com" not in emails


def test_admin_cannot_retrieve_cross_tenant_user(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")
    victim_b = make_user(org_b, role=Role.STUDENT, email="victim@b.com")

    resp = auth_client(admin_a).get(f"/api/users/{victim_b.id}/")
    assert resp.status_code == 404  # not a leak — cleanly not found


def test_admin_cannot_update_cross_tenant_user(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")
    victim_b = make_user(org_b, role=Role.STUDENT, email="victim@b.com")

    resp = auth_client(admin_a).patch(
        f"/api/users/{victim_b.id}/", {"full_name": "hacked"}, format="json"
    )
    assert resp.status_code == 404
    victim_b.refresh_from_db()
    assert victim_b.full_name != "hacked"


def test_admin_cannot_deactivate_cross_tenant_user(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")
    victim_b = make_user(org_b, role=Role.STUDENT, email="victim@b.com")

    resp = auth_client(admin_a).delete(f"/api/users/{victim_b.id}/")
    assert resp.status_code == 404
    victim_b.refresh_from_db()
    assert victim_b.is_active is True


def test_admin_creates_user_in_own_tenant(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")

    resp = auth_client(admin_a).post(
        "/api/users/",
        {
            "email": "new@a.com",
            "full_name": "New Teacher",
            "role": Role.TEACHER,
            "password": "Passw0rd!123",
        },
        format="json",
    )
    assert resp.status_code == 201
    created = User.objects.get(email="new@a.com")
    # Landed in the admin's org even though org was never in the payload.
    assert created.organization_id == org_a.id


def test_admin_cannot_plant_user_in_other_tenant_via_payload(org_a, org_b, make_user, auth_client):
    admin_a = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com")

    resp = auth_client(admin_a).post(
        "/api/users/",
        {
            "email": "sneaky@x.com",
            "role": Role.STUDENT,
            "password": "Passw0rd!123",
            "organization": org_b.id,  # attempt to target the other tenant
        },
        format="json",
    )
    assert resp.status_code == 201
    assert User.objects.get(email="sneaky@x.com").organization_id == org_a.id
