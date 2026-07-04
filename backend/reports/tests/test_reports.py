import pytest
from django.utils import timezone

from accounts.constants import Role
from attempts.models import Attempt
from reports.services.progress import _trend, student_papers
from tenants.context import tenant_context

pytestmark = pytest.mark.django_db


# ---- pure aggregation helper (no DB) ----

def test_trend_classification():
    assert _trend([10, 90]) == "improving"
    assert _trend([90, 10]) == "declining"
    assert _trend([70, 72]) == "steady"
    assert _trend([50]) == "insufficient_data"


def _attempt(org, learner, question, score):
    with tenant_context(org):
        return Attempt.objects.create(
            learner=learner,
            question=question,
            submitted_answer="x",
            score=score,
            graded_at=timezone.now(),
        )


def test_student_papers_one_mark_per_question(report_setup, org_a):
    with tenant_context(org_a):
        result = student_papers(report_setup["student"])
    assert result["summary"]["papers"] == 1
    paper = result["papers"][0]
    assert paper["answered"] == 4
    assert paper["total_questions"] == 5
    assert paper["marks"] == 2.4
    assert paper["total_marks"] == 5
    assert result["summary"]["total_marks"] == 2.4
    assert result["summary"]["total_possible"] == 5


def test_marks_use_best_attempt_per_question(org_a, make_user, make_material, make_question):
    student = make_user(org_a, role=Role.STUDENT, email="re@a.com")
    material = make_material(org_a)
    q = make_question(org_a, material, topic_or_category="algebra", question_text="q1")
    # Same question answered twice: 30 then 80. Best (80) counts once, not 30+80.
    _attempt(org_a, student, q, 30)
    _attempt(org_a, student, q, 80)
    with tenant_context(org_a):
        result = student_papers(student)
    paper = result["papers"][0]
    assert paper["answered"] == 1        # one distinct question
    assert paper["marks"] == 0.8         # best 80/100, not (0.3 + 0.8)


def test_my_papers_endpoint_returns_own_marks(report_setup, org_a, auth_client):
    resp = auth_client(report_setup["student"]).get("/api/reports/my-papers/")
    assert resp.status_code == 200
    assert resp.json()["data"]["summary"]["total_marks"] == 2.4


def test_my_papers_forbidden_for_non_learner(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")
    resp = auth_client(teacher).get("/api/reports/my-papers/")
    assert resp.status_code == 403


@pytest.fixture
def report_setup(org_a, make_user, make_material, make_question):
    student = make_user(org_a, role=Role.STUDENT, email="s@a.com")
    material = make_material(org_a)

    alg1 = make_question(org_a, material, topic_or_category="algebra", question_text="alg1")
    alg2 = make_question(org_a, material, topic_or_category="algebra", question_text="alg2")
    geo1 = make_question(org_a, material, topic_or_category="geometry", question_text="geo1")
    geo2 = make_question(org_a, material, topic_or_category="geometry", question_text="geo2")
    make_question(org_a, material, topic_or_category="calculus", question_text="calc1")  # untested

    _attempt(org_a, student, alg1, 80)
    _attempt(org_a, student, alg2, 90)
    _attempt(org_a, student, geo1, 30)
    _attempt(org_a, student, geo2, 40)
    return {"student": student, "material": material}


def test_learner_report_classifies_topics(org_a, make_user, auth_client, report_setup):
    student = report_setup["student"]
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")

    resp = auth_client(teacher).get(f"/api/reports/learner/{student.id}/")
    assert resp.status_code == 200
    data = resp.json()["data"]

    strong_topics = {t["topic"] for t in data["topics"]["strong"]}
    weak_topics = {t["topic"] for t in data["topics"]["weak"]}
    assert "algebra" in strong_topics       # avg 85
    assert "geometry" in weak_topics        # avg 35
    assert "calculus" in data["topics"]["untested"]
    assert data["summary"]["graded_attempts"] == 4
    assert data["summary"]["overall_avg"] == 60.0  # (80+90+30+40)/4


# ---- access control ----

def test_learner_sees_own_report(org_a, auth_client, report_setup):
    student = report_setup["student"]
    resp = auth_client(student).get(f"/api/reports/learner/{student.id}/")
    assert resp.status_code == 200


def test_other_learner_forbidden(org_a, make_user, auth_client, report_setup):
    student = report_setup["student"]
    other = make_user(org_a, role=Role.STUDENT, email="other@a.com")
    resp = auth_client(other).get(f"/api/reports/learner/{student.id}/")
    assert resp.status_code == 403


def test_parent_sees_only_linked_learner(org_a, make_user, auth_client, report_setup):
    student = report_setup["student"]
    linked_parent = make_user(org_a, role=Role.PARENT, email="p1@a.com", linked_learner=student)
    unlinked_parent = make_user(org_a, role=Role.PARENT, email="p2@a.com")

    assert auth_client(linked_parent).get(f"/api/reports/learner/{student.id}/").status_code == 200
    assert auth_client(unlinked_parent).get(f"/api/reports/learner/{student.id}/").status_code == 403


def test_cross_tenant_learner_report_is_404(org_a, org_b, make_user, auth_client, report_setup):
    student = report_setup["student"]  # in org_a
    teacher_b = make_user(org_b, role=Role.MENTOR, email="m@b.com")
    resp = auth_client(teacher_b).get(f"/api/reports/learner/{student.id}/")
    assert resp.status_code == 404


# ---- dashboard ----

def test_teacher_dashboard_lists_tenant_learners(org_a, make_user, auth_client, report_setup):
    make_user(org_a, role=Role.STUDENT, email="s2@a.com")  # a second learner
    teacher = make_user(org_a, role=Role.TEACHER, email="t@a.com")

    resp = auth_client(teacher).get("/api/reports/dashboard/")
    assert resp.status_code == 200
    rows = resp.json()["data"]
    emails = {r["learner"]["email"] for r in rows}
    assert {"s@a.com", "s2@a.com"} <= emails
    # The graded student carries an overall average.
    graded_row = next(r for r in rows if r["learner"]["email"] == "s@a.com")
    assert graded_row["overall_avg"] == 60.0


def test_parent_dashboard_shows_only_linked(org_a, make_user, auth_client, report_setup):
    student = report_setup["student"]
    parent = make_user(org_a, role=Role.PARENT, email="p@a.com", linked_learner=student)
    rows = auth_client(parent).get("/api/reports/dashboard/").json()["data"]
    assert {r["learner"]["id"] for r in rows} == {student.id}


def test_dashboard_is_tenant_scoped(org_a, org_b, make_user, auth_client, report_setup):
    # org_b teacher sees none of org_a's learners.
    teacher_b = make_user(org_b, role=Role.TEACHER, email="t@b.com")
    rows = auth_client(teacher_b).get("/api/reports/dashboard/").json()["data"]
    assert rows == []
