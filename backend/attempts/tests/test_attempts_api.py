import pytest

from accounts.constants import Role

pytestmark = pytest.mark.django_db


def test_learner_submits_answer_to_own_tenant_question(org_a, make_user, make_material, make_question, auth_client):
    student = make_user(org_a, role=Role.STUDENT, email="s@a.com")
    q = make_question(org_a, make_material(org_a))

    resp = auth_client(student).post(
        "/api/attempts/",
        {"question": q.id, "submitted_answer": "My answer."},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["learner"] == student.id
    assert body["is_graded"] is False  # grading happens asynchronously


def test_non_learner_cannot_submit(org_a, make_user, make_material, make_question, auth_client):
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    q = make_question(org_a, make_material(org_a))
    resp = auth_client(teacher).post(
        "/api/attempts/", {"question": q.id, "submitted_answer": "x"}, format="json"
    )
    assert resp.status_code == 403


def test_cannot_answer_other_tenant_question(org_a, org_b, make_user, make_material, make_question, auth_client):
    student_b = make_user(org_b, role=Role.STUDENT, email="s@b.com")
    q_a = make_question(org_a, make_material(org_a))

    resp = auth_client(student_b).post(
        "/api/attempts/", {"question": q_a.id, "submitted_answer": "leak?"}, format="json"
    )
    assert resp.status_code == 400  # question not in tenant B's scope


def _submit(client, question_id, answer="ans"):
    return client.post(
        "/api/attempts/", {"question": question_id, "submitted_answer": answer}, format="json"
    )


def test_learner_sees_only_their_own_attempts(org_a, make_user, make_material, make_question, auth_client):
    q = make_question(org_a, make_material(org_a))
    s1 = make_user(org_a, role=Role.STUDENT, email="s1@a.com")
    s2 = make_user(org_a, role=Role.STUDENT, email="s2@a.com")

    a1 = _submit(auth_client(s1), q.id).json()["data"]["id"]
    _submit(auth_client(s2), q.id)

    # s1 lists -> only their own attempt.
    resp = auth_client(s1).get("/api/attempts/")
    ids = {row["id"] for row in resp.json()["results"]}
    assert ids == {a1}

    # s2 cannot retrieve s1's attempt (same tenant, different learner) -> 404.
    assert auth_client(s2).get(f"/api/attempts/{a1}/").status_code == 404


def test_teacher_sees_all_attempts_in_tenant(org_a, make_user, make_material, make_question, auth_client):
    q = make_question(org_a, make_material(org_a))
    s1 = make_user(org_a, role=Role.STUDENT, email="s1@a.com")
    s2 = make_user(org_a, role=Role.STUDENT, email="s2@a.com")
    _submit(auth_client(s1), q.id)
    _submit(auth_client(s2), q.id)

    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    resp = auth_client(teacher).get("/api/attempts/")
    assert resp.json()["count"] == 2


def test_cross_tenant_attempt_retrieve_is_404(org_a, org_b, make_user, make_material, make_question, auth_client):
    q_a = make_question(org_a, make_material(org_a))
    s_a = make_user(org_a, role=Role.STUDENT, email="s@a.com")
    attempt_id = _submit(auth_client(s_a), q_a.id).json()["data"]["id"]

    # An observer in tenant B must not be able to read tenant A's attempt.
    mentor_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    assert auth_client(mentor_b).get(f"/api/attempts/{attempt_id}/").status_code == 404
