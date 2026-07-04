import pytest

from accounts.constants import Role
from rest_framework_simplejwt.tokens import AccessToken

pytestmark = pytest.mark.django_db


def test_login_succeeds_and_embeds_tenant_and_role_claims(api_client, org_a, make_user):
    user = make_user(org_a, role=Role.ORG_ADMIN, email="admin@a.com", password="Passw0rd!123")

    resp = api_client.post(
        "/api/auth/login/",
        {"email": "admin@a.com", "password": "Passw0rd!123"},
        format="json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] is True
    data = body["data"]
    assert "access" in data and "refresh" in data
    assert data["tenant_id"] == org_a.id
    assert data["role"] == Role.ORG_ADMIN

    # The signed access token itself carries tenant_id (what the middleware reads).
    claims = AccessToken(data["access"])
    assert claims["tenant_id"] == org_a.id
    assert claims["role"] == Role.ORG_ADMIN


def test_login_with_wrong_password_is_401(api_client, org_a, make_user):
    make_user(org_a, role=Role.STUDENT, email="s@a.com", password="Passw0rd!123")
    resp = api_client.post(
        "/api/auth/login/",
        {"email": "s@a.com", "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401
    assert resp.json()["status"] is False


def test_login_is_throttled_against_brute_force(api_client, org_a, make_user):
    make_user(org_a, role=Role.STUDENT, email="bf@a.com", password="Passw0rd!123")
    # Default rate is 10/min; the 11th attempt from the same client is blocked.
    codes = [
        api_client.post(
            "/api/auth/login/",
            {"email": "bf@a.com", "password": "wrong"},
            format="json",
        ).status_code
        for _ in range(11)
    ]
    assert 429 in codes  # brute-force protection kicked in


def test_me_requires_authentication(api_client):
    assert api_client.get("/api/auth/me/").status_code == 401


def test_me_returns_current_user(org_a, make_user, auth_client):
    user = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    resp = auth_client(user).get("/api/auth/me/")
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "t@a.com"
