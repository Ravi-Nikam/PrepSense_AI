import pytest

from accounts.constants import Role
from attempts.models import Attempt

pytestmark = pytest.mark.django_db


def _make_graded_setup(org, make_user, make_material, make_question):
    student = make_user(org, role=Role.STUDENT, email="s@a.com")
    material = make_material(org)
    # Reference answer contains the words the fake grader rewards overlap with.
    q = make_question(
        org, material,
        question_text="Explain rate limiting.",
        reference_answer="token bucket sliding window per tenant keys",
    )
    return student, q


def test_submitting_answer_returns_ungraded_snapshot(org_a, make_user, make_material, make_question, auth_client):
    student, q = _make_graded_setup(org_a, make_user, make_material, make_question)
    resp = auth_client(student).post(
        "/api/attempts/", {"question": q.id, "submitted_answer": "token bucket"}, format="json"
    )
    assert resp.status_code == 201
    # The response is the pre-grading snapshot (async semantics).
    assert resp.json()["data"]["is_graded"] is False


def test_grading_fills_score_and_feedback(org_a, make_user, make_material, make_question, auth_client):
    student, q = _make_graded_setup(org_a, make_user, make_material, make_question)
    resp = auth_client(student).post(
        "/api/attempts/",
        {"question": q.id, "submitted_answer": "token bucket sliding window per tenant keys"},
        format="json",
    )
    attempt_id = resp.json()["data"]["id"]

    # Eager grading has run against the DB row.
    attempt = Attempt.all_objects.get(id=attempt_id)
    assert attempt.is_graded
    assert attempt.score == 100  # full overlap with the reference
    assert attempt.feedback
    assert attempt.graded_at is not None


def test_grade_reflects_answer_quality(org_a, make_user, make_material, make_question, auth_client):
    student, q = _make_graded_setup(org_a, make_user, make_material, make_question)
    resp = auth_client(student).post(
        "/api/attempts/",
        {"question": q.id, "submitted_answer": "no idea, something unrelated"},
        format="json",
    )
    attempt = Attempt.all_objects.get(id=resp.json()["data"]["id"])
    assert attempt.is_graded
    assert attempt.score < 50  # weak answer scores low


def test_learner_can_read_own_graded_attempt(org_a, make_user, make_material, make_question, auth_client):
    student, q = _make_graded_setup(org_a, make_user, make_material, make_question)
    client = auth_client(student)
    attempt_id = client.post(
        "/api/attempts/", {"question": q.id, "submitted_answer": "token bucket"}, format="json"
    ).json()["data"]["id"]

    resp = client.get(f"/api/attempts/{attempt_id}/")
    assert resp.status_code == 200
    assert resp.json()["data"]["is_graded"] is True
