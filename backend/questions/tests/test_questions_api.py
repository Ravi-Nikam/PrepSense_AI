import pytest

from accounts.constants import Role
from questions.constants import QuestionCategory

pytestmark = pytest.mark.django_db


def test_uploader_creates_question_for_own_material(org_a, make_user, make_material, auth_client):
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    material = make_material(org_a, uploaded_by=teacher)

    resp = auth_client(teacher).post(
        "/api/questions/",
        {
            "source_material": material.id,
            "topic_or_category": "system design",
            "category": QuestionCategory.TECHNICAL,
            "question_text": "Design a URL shortener.",
        },
        format="json",
    )
    assert resp.status_code == 201
    # mode is derived from the material, never the client.
    assert resp.json()["data"]["mode"] == material.mode


def test_learner_cannot_manage_questions(org_a, make_user, auth_client):
    candidate = make_user(org_a, role=Role.CANDIDATE, email="c@a.com")
    assert auth_client(candidate).get("/api/questions/").status_code == 403


def test_cannot_create_question_against_other_tenant_material(org_a, org_b, make_user, make_material, auth_client):
    teacher_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    material_a = make_material(org_a)

    resp = auth_client(teacher_b).post(
        "/api/questions/",
        {
            "source_material": material_a.id,
            "topic_or_category": "x",
            "category": QuestionCategory.TECHNICAL,
            "question_text": "leak?",
        },
        format="json",
    )
    assert resp.status_code == 400  # source_material not in tenant B's scope


def test_list_only_returns_own_tenant_questions(org_a, org_b, make_user, make_material, make_question, auth_client):
    teacher_a = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    mat_a = make_material(org_a)
    make_question(org_a, mat_a, question_text="A-question")
    mat_b = make_material(org_b)
    make_question(org_b, mat_b, question_text="B-question")

    resp = auth_client(teacher_a).get("/api/questions/")
    texts = {row["question_text"] for row in resp.json()["results"]}
    assert texts == {"A-question"}


def test_cross_tenant_retrieve_is_404(org_a, org_b, make_user, make_material, make_question, auth_client):
    teacher_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    mat_a = make_material(org_a)
    q_a = make_question(org_a, mat_a)

    resp = auth_client(teacher_b).get(f"/api/questions/{q_a.id}/")
    assert resp.status_code == 404
