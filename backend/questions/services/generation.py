import logging

from core.services.embeddings import get_embedding_provider, is_duplicate
from core.services.llm import get_llm_client
from core.services.retrieval import top_k_chunks
from questions.constants import Difficulty, QuestionCategory
from questions.models import Question
from tenants.constants import PrepContext

logger = logging.getLogger("prepcheck.questions")

DEDUP_THRESHOLD = 0.95


def generate_for_material(material, count=5, difficulty=None, category=None, start_index=None):
    # Retrieve the top-K chunks most relevant to the material's topic and ground the
    # LLM in those (falls back to all chunks for a small/thin source).
    query = material.topic or material.subject_or_role or ""
    chunks = top_k_chunks(material, query)
    contexts = [c.chunk_text for c in chunks]
    chunk_by_text = {c.chunk_text: c for c in chunks}

    existing_qs = Question.objects.filter(source_material=material)
    if start_index is None:
        start_index = existing_qs.count()

    llm = get_llm_client()
    embedder = get_embedding_provider()

    specs = llm.generate_questions(
        mode=material.mode,
        context_chunks=contexts,
        count=count,
        topic=material.topic or material.subject_or_role,
        start_index=start_index,
    )

    existing_vecs = [
        q.embedding for q in existing_qs.exclude(embedding__isnull=True)
    ]

    created = []
    for spec in specs:
        q_text = spec["question_text"]
        vec = embedder.embed_one(q_text)
        if is_duplicate(vec, existing_vecs, DEDUP_THRESHOLD):
            logger.info(
                "Skipped near-duplicate generated question",
                extra={"tenant": material.tenant_id, "user": material.uploaded_by_id},
            )
            continue

        question = Question(
            source_material=material,
            source_chunk=chunk_by_text.get(spec.get("_chunk_text")),
            mode=material.mode,
            topic_or_category=spec.get("topic_or_category") or (material.topic or "general"),
            question_text=q_text,
            reference_answer=spec.get("reference_answer", ""),
            embedding=vec,
        )
        if material.mode == PrepContext.EXAM:
            question.difficulty = difficulty or Difficulty.MEDIUM
        else:
            question.category = category or QuestionCategory.TECHNICAL
        question.save()  # tenant auto-stamped from context

        existing_vecs.append(vec)
        created.append(question)

    logger.info(
        "Generated %s questions (%s requested)",
        len(created),
        count,
        extra={"tenant": material.tenant_id, "user": material.uploaded_by_id},
    )
    return created


def generate_paper(material, target, difficulty=None, category=None, batch=25, max_rounds=8):
    created = []
    rounds = 0
    while len(created) < target and rounds < max_rounds:
        need = min(batch, target - len(created))
        made = generate_for_material(material, count=need, difficulty=difficulty, category=category)
        created.extend(made)
        rounds += 1
        if not made:
            break  # dedup exhausted — the material can't yield more unique questions
    logger.info(
        "Paper generation: %s/%s questions in %s round(s)",
        len(created),
        target,
        rounds,
        extra={"tenant": material.tenant_id, "user": material.uploaded_by_id},
    )
    return created
