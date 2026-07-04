import pytest

from accounts.constants import Role
from questions.models import Question

pytestmark = pytest.mark.django_db

LONG_JD = "We need a backend engineer skilled in Django Postgres and Celery. " * 40


def _ready_material_with_questions(client_teacher, org):
    from materials.models import SourceMaterial
    from tenants.constants import PrepContext

    resp = client_teacher.post(
        "/api/materials/",
        {"mode": PrepContext.INTERVIEW, "subject_or_role": "Backend Engineer", "source_text": LONG_JD},
        format="json",
    )
    material_id = resp.json()["data"]["id"]
    client_teacher.post(f"/api/materials/{material_id}/generate/", {"count": 3}, format="json")
    return material_id


def test_next_question_hides_reference_answer(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    material_id = _ready_material_with_questions(auth_client(teacher), org_a)

    student = make_user(org_a, role=Role.CANDIDATE, email="c@a.com")
    resp = auth_client(student).get(f"/api/practice/next/?material={material_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data is not None
    assert "reference_answer" not in data  # rubric must not leak to the learner


def test_next_excludes_already_attempted(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    material_id = _ready_material_with_questions(auth_client(teacher), org_a)
    student = make_user(org_a, role=Role.CANDIDATE, email="c@a.com")
    client = auth_client(student)

    first_id = client.get(f"/api/practice/next/?material={material_id}").json()["data"]["id"]
    client.post("/api/attempts/", {"question": first_id, "submitted_answer": "x"}, format="json")

    # Next call must return a DIFFERENT question (the attempted one is excluded).
    second = client.get(f"/api/practice/next/?material={material_id}").json()["data"]
    assert second is None or second["id"] != first_id


def test_non_learner_cannot_use_practice(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    assert auth_client(teacher).get("/api/practice/next/").status_code == 403


def test_refresh_generates_new_question(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    material_id = _ready_material_with_questions(auth_client(teacher), org_a)
    before = Question.all_objects.filter(source_material_id=material_id).count()

    student = make_user(org_a, role=Role.CANDIDATE, email="c@a.com")
    resp = auth_client(student).post("/api/practice/refresh/", {"material": material_id}, format="json")
    assert resp.status_code == 201
    assert "reference_answer" not in resp.json()["data"]

    after = Question.all_objects.filter(source_material_id=material_id).count()
    assert after == before + 1  # a genuinely new question was added


def test_refresh_blocked_cross_tenant(org_a, org_b, make_user, make_material, auth_client):
    material_a = make_material(org_a)
    candidate_b = make_user(org_b, role=Role.CANDIDATE, email="c@b.com")
    resp = auth_client(candidate_b).post(
        "/api/practice/refresh/", {"material": material_a.id}, format="json"
    )
    assert resp.status_code == 404  # material_a invisible to tenant B


def test_next_is_tenant_scoped(org_a, org_b, make_user, auth_client):
    teacher_a = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    material_a = _ready_material_with_questions(auth_client(teacher_a), org_a)

    # A candidate in B asking for A's material sees nothing (scoped away).
    candidate_b = make_user(org_b, role=Role.CANDIDATE, email="c@b.com")
    resp = auth_client(candidate_b).get(f"/api/practice/next/?material={material_a}")
    assert resp.status_code == 200
    assert resp.json()["data"] is None
