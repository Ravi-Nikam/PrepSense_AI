from attempts.models import Attempt
from questions.models import Question

STRONG_MIN = 70  # avg score >= this -> strong
WEAK_MAX = 50    # avg score < this  -> weak
TREND_DELTA = 5  # min avg-score change (later vs earlier half) to call a trend


def _trend(ordered_scores):
    scores = [s for s in ordered_scores if s is not None]
    if len(scores) < 2:
        return "insufficient_data"
    mid = len(scores) // 2
    earlier = scores[:mid] or scores[:1]
    later = scores[mid:]
    a = sum(earlier) / len(earlier)
    b = sum(later) / len(later)
    if b - a >= TREND_DELTA:
        return "improving"
    if a - b >= TREND_DELTA:
        return "declining"
    return "steady"


def learner_report(learner):
    attempts = list(
        Attempt.objects.filter(learner=learner)
        .order_by("created_at")
        .values("score", "created_at", "question__topic_or_category")
    )
    graded = [a for a in attempts if a["score"] is not None]

    by_topic = {}
    for a in graded:
        by_topic.setdefault(a["question__topic_or_category"], []).append(a["score"])

    topic_stats = []
    for topic, scores in by_topic.items():
        avg = sum(scores) / len(scores)
        topic_stats.append(
            {
                "topic": topic,
                "attempts": len(scores),
                "avg_score": round(avg, 1),
                "best_score": max(scores),
                "trend": _trend(scores),
            }
        )
    topic_stats.sort(key=lambda x: x["avg_score"])

    strong = [t for t in topic_stats if t["avg_score"] >= STRONG_MIN]
    weak = [t for t in topic_stats if t["avg_score"] < WEAK_MAX]
    developing = [t for t in topic_stats if WEAK_MAX <= t["avg_score"] < STRONG_MIN]

    all_topics = set(Question.objects.values_list("topic_or_category", flat=True).distinct())
    untested = sorted(all_topics - set(by_topic))

    overall_avg = round(sum(a["score"] for a in graded) / len(graded), 1) if graded else None

    return {
        "learner": {
            "id": learner.id,
            "email": learner.email,
            "full_name": learner.full_name,
            "role": learner.role,
        },
        "summary": {
            "total_attempts": len(attempts),
            "graded_attempts": len(graded),
            "overall_avg": overall_avg,
            "trend": _trend([a["score"] for a in graded]),
        },
        "topics": {
            "strong": strong,
            "developing": developing,
            "weak": weak,
            "untested": untested,
        },
    }


def student_papers(learner):
    rows = list(
        Attempt.objects.filter(learner=learner, score__isnull=False)
        .values(
            "score",
            "question_id",
            "question__source_material_id",
            "question__source_material__subject_or_role",
            "question__source_material__topic",
            "question__source_material__mode",
        )
    )

    by_paper = {}
    for r in rows:
        pid = r["question__source_material_id"]
        paper = by_paper.setdefault(
            pid,
            {
                "material_id": pid,
                "subject_or_role": r["question__source_material__subject_or_role"],
                "topic": r["question__source_material__topic"] or "general",
                "mode": r["question__source_material__mode"],
                "best": {},  # question_id -> best score
            },
        )
        qid = r["question_id"]
        paper["best"][qid] = max(paper["best"].get(qid, 0), r["score"])

    # Total marks per paper = number of questions in that material (1 mark each).
    totals = {
        pid: Question.objects.filter(source_material_id=pid).count()
        for pid in by_paper
    }

    papers = []
    for pid, p in by_paper.items():
        best = p.pop("best")
        scores = list(best.values())            # one best score per answered question
        earned = sum(s / 100 for s in scores)   # each question worth 1 mark
        total = totals.get(pid, len(scores))
        papers.append(
            {
                **p,
                "answered": len(scores),           # distinct questions answered
                "total_questions": total,
                "avg_score": round(sum(scores) / len(scores), 1),
                "marks": round(earned, 1),
                "total_marks": total,  # 1 mark per question
            }
        )
    papers.sort(key=lambda x: x["marks"])  # weakest paper first

    total_possible = sum(p["total_marks"] for p in papers)
    total_marks = round(sum(p["marks"] for p in papers), 1)

    return {
        "learner": {
            "id": learner.id,
            "email": learner.email,
            "full_name": learner.full_name,
        },
        "summary": {
            "papers": len(papers),
            "total_marks": total_marks,
            "total_possible": total_possible,
        },
        "papers": papers,
    }


def dashboard_rows(learners):
    rows = []
    for learner in learners:
        report = learner_report(learner)
        rows.append(
            {
                "learner": report["learner"],
                **report["summary"],
                "weak_topic_count": len(report["topics"]["weak"]),
                "strong_topic_count": len(report["topics"]["strong"]),
            }
        )
    # Surface the learners who need attention first.
    rows.sort(key=lambda r: (r["overall_avg"] is None, r["overall_avg"] or 0))
    return rows
