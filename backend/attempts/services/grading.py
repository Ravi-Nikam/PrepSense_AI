import logging

from django.utils import timezone

from core.services.llm import get_llm_client
from core.services.retrieval import top_k_chunks

logger = logging.getLogger("prepcheck.attempts")


def grade(attempt):
    question = attempt.question
    # Ground grading in the chunks most relevant to this question (top-K retrieval).
    chunk_texts = [c.chunk_text for c in top_k_chunks(question.source_material, question.question_text)]
    context = "\n\n".join(chunk_texts) if chunk_texts else (
        question.source_chunk.chunk_text if question.source_chunk_id else ""
    )

    result = get_llm_client().grade_answer(
        question_text=question.question_text,
        reference_answer=question.reference_answer,
        submitted_answer=attempt.submitted_answer,
        context=context,
    )

    attempt.score = int(result.get("score", 0))
    feedback = result.get("feedback", "")
    missing = result.get("missing_points") or []
    if missing:
        feedback = f"{feedback} Missing: {', '.join(missing)}."
    attempt.feedback = feedback
    attempt.graded_at = timezone.now()
    attempt.save(update_fields=["score", "feedback", "graded_at", "updated_at"])
    logger.info(
        "Answer graded (score=%s)",
        attempt.score,
        extra={"tenant": attempt.tenant_id, "user": attempt.learner_id},
    )
    return attempt.score
