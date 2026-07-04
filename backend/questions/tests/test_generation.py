import pytest

from accounts.constants import Role
from questions.constants import QuestionCategory
from questions.models import Question
from tenants.constants import PrepContext

pytestmark = pytest.mark.django_db

LONG_JD = "We need a backend engineer skilled in Django Postgres and Celery. " * 40


def _upload_ready_material(client):
    resp = client.post(
        "/api/materials/",
        {"mode": PrepContext.INTERVIEW, "subject_or_role": "Backend Engineer", "source_text": LONG_JD},
        format="json",
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def test_generate_creates_grounded_tagged_questions(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    client = auth_client(teacher)
    material_id = _upload_ready_material(client)

    resp = client.post(f"/api/materials/{material_id}/generate/", {"count": 5}, format="json")
    assert resp.status_code == 202

    questions = list(Question.all_objects.filter(source_material_id=material_id))
    assert len(questions) >= 1
    for q in questions:
        assert q.tenant_id == org_a.id
        assert q.mode == PrepContext.INTERVIEW
        # Interview questions are category-tagged and carry no exam difficulty.
        assert q.category == QuestionCategory.TECHNICAL
        assert q.difficulty is None
    # Grounded: at least one question echoes vocabulary from the source JD.
    assert any("backend" in q.question_text.lower() for q in questions)


def test_generation_deduplicates_identical_questions(org_a, make_user, auth_client):
    from materials.models import SourceMaterial
    from questions.services.generation import generate_for_material
    from tenants.context import tenant_context

    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    material_id = _upload_ready_material(auth_client(teacher))

    with tenant_context(org_a):
        material = SourceMaterial.objects.get(id=material_id)
        first = generate_for_material(material, count=3, start_index=0)
        assert len(first) == 3
        # Same start_index -> identical question text -> all recognised as duplicates.
        again = generate_for_material(material, count=3, start_index=0)
        assert len(again) == 0


def test_regeneration_via_endpoint_adds_new_questions(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    client = auth_client(teacher)
    material_id = _upload_ready_material(client)

    client.post(f"/api/materials/{material_id}/generate/", {"count": 3}, format="json")
    first = Question.all_objects.filter(source_material_id=material_id).count()
    client.post(f"/api/materials/{material_id}/generate/", {"count": 3}, format="json")
    second = Question.all_objects.filter(source_material_id=material_id).count()
    assert second > first


def test_generate_on_unready_material_is_409(org_a, make_user, make_material, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    # Created directly (no ingestion) -> status PENDING.
    material = make_material(org_a, uploaded_by=teacher)

    resp = auth_client(teacher).post(f"/api/materials/{material.id}/generate/", {}, format="json")
    assert resp.status_code == 409


def test_generate_is_blocked_cross_tenant(org_a, org_b, make_user, make_material, auth_client):
    mentor_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    material_a = make_material(org_a)
    resp = auth_client(mentor_b).post(f"/api/materials/{material_a.id}/generate/", {}, format="json")
    assert resp.status_code == 404


def test_learner_cannot_trigger_generation(org_a, make_user, make_material, auth_client):
    student = make_user(org_a, role=Role.STUDENT, email="s@a.com")
    material = make_material(org_a)
    resp = auth_client(student).post(f"/api/materials/{material.id}/generate/", {}, format="json")
    assert resp.status_code == 403


def test_per_tenant_daily_llm_cap_enforced(org_a, make_user, auth_client):
    org_a.llm_daily_call_cap = 1
    org_a.save()

    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    client = auth_client(teacher)
    material_id = _upload_ready_material(client)

    first = client.post(f"/api/materials/{material_id}/generate/", {"count": 2}, format="json")
    assert first.status_code == 202
    second = client.post(f"/api/materials/{material_id}/generate/", {"count": 2}, format="json")
    assert second.status_code == 429  # daily cap hit


def test_per_tenant_monthly_llm_cap_enforced(org_a, make_user, auth_client):
    org_a.llm_daily_call_cap = 100   # plenty of daily headroom
    org_a.llm_monthly_call_cap = 1   # but the month is capped at 1
    org_a.save()

    teacher = make_user(org_a, role=Role.MENTOR, email="mm@a.com")
    client = auth_client(teacher)
    material_id = _upload_ready_material(client)

    first = client.post(f"/api/materials/{material_id}/generate/", {"count": 2}, format="json")
    assert first.status_code == 202
    second = client.post(f"/api/materials/{material_id}/generate/", {"count": 2}, format="json")
    assert second.status_code == 429  # monthly cap hit despite daily headroom
