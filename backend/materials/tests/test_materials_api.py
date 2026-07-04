import pytest

from accounts.constants import Role
from tenants.constants import PrepContext

pytestmark = pytest.mark.django_db


def _create_material(client, **over):
    payload = {
        "mode": PrepContext.INTERVIEW,
        "subject_or_role": "Backend Engineer",
        "source_text": "Django + Postgres backend role.",
    }
    payload.update(over)
    return client.post("/api/materials/", payload, format="json")


def test_uploader_creates_material_scoped_to_own_tenant(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    resp = _create_material(auth_client(teacher))
    assert resp.status_code == 201
    assert resp.json()["data"]["mode"] == PrepContext.INTERVIEW


def test_learner_cannot_manage_materials(org_a, make_user, auth_client):
    student = make_user(org_a, role=Role.STUDENT, email="s@a.com")
    assert auth_client(student).get("/api/materials/").status_code == 403
    assert _create_material(auth_client(student)).status_code == 403


def test_exam_material_requires_file(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    resp = _create_material(auth_client(teacher), mode=PrepContext.EXAM, source_text="")
    assert resp.status_code == 400  # no PDF attached


def test_list_only_returns_own_tenant_materials(org_a, org_b, make_user, make_material, auth_client):
    teacher_a = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    make_material(org_a, uploaded_by=teacher_a, subject_or_role="A-role")
    make_material(org_b, subject_or_role="B-role")

    resp = auth_client(teacher_a).get("/api/materials/")
    assert resp.status_code == 200
    roles = {row["subject_or_role"] for row in resp.json()["results"]}
    assert roles == {"A-role"}


def test_cross_tenant_retrieve_is_404(org_a, org_b, make_user, make_material, auth_client):
    teacher_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    material_a = make_material(org_a)

    resp = auth_client(teacher_b).get(f"/api/materials/{material_a.id}/")
    assert resp.status_code == 404


def test_cross_tenant_delete_is_404_and_row_survives(org_a, org_b, make_user, make_material, auth_client):
    from materials.models import SourceMaterial

    teacher_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    material_a = make_material(org_a)

    resp = auth_client(teacher_b).delete(f"/api/materials/{material_a.id}/")
    assert resp.status_code == 404
    assert SourceMaterial.all_objects.filter(id=material_a.id).exists()
