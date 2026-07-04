import json
import logging
import re

from django.conf import settings

from tenants.constants import PrepContext

logger = logging.getLogger("prepcheck.llm")

GENERATION_SYSTEM_PROMPT = (
    "You are an assessment author. Generate questions grounded ONLY in the "
    "provided source context. Do not introduce facts, requirements, or topics "
    "that are not present in the source. Return strict JSON."
)
GRADING_SYSTEM_PROMPT = (
    "You are a strict but fair grader. Judge the answer ONLY against the provided "
    "reference/rubric and source context. Do not reward correct-sounding claims "
    "that are not supported by the source. Return strict JSON."
)


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


class LLMClient:
    def generate_questions(self, *, mode, context_chunks, count, topic=None, tag=None, start_index=0):
        raise NotImplementedError

    def grade_answer(self, *, question_text, reference_answer, submitted_answer, context=""):
        raise NotImplementedError


class FakeLLMClient(LLMClient):

    def generate_questions(self, *, mode, context_chunks, count, topic=None, tag=None, start_index=0):
        chunks = [c for c in context_chunks if c and c.strip()] or ["the provided material"]
        out = []
        for i in range(count):
            n = start_index + i
            chunk = chunks[n % len(chunks)]
            snippet = " ".join(chunk.strip().split())[:120]
            out.append(
                {
                    "question_text": f"Based on the source, explain: {snippet} (aspect {n + 1})",
                    "reference_answer": f"A correct answer references: {snippet}",
                    "topic_or_category": topic or "general",
                }
            )
        return out

    def grade_answer(self, *, question_text, reference_answer, submitted_answer, context=""):
        ref = _tokens(reference_answer) or _tokens(context)
        ans = _tokens(submitted_answer)
        if not ref:
            score = 0
        else:
            overlap = len(ref & ans) / len(ref)
            score = int(round(min(1.0, overlap) * 100))
        if score >= 80:
            feedback = "Strong: covers the key points from the source."
        elif score >= 50:
            feedback = "Partial: some key points present; several from the source are missing."
        else:
            feedback = "Weak: misses most of the points the source expects."
        missing = sorted(ref - ans)[:5]
        return {
            "score": score,
            "feedback": feedback,
            "missing_points": missing,
        }


class AnthropicLLMClient(LLMClient):

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def _client(self):
        import anthropic

        # Bounded timeout so a hung request can't wedge a worker.
        return anthropic.Anthropic(api_key=self.api_key, timeout=30.0)

    def _complete_json(self, system, user):
        from core.services.resilience import retry_call

        message = retry_call(
            lambda: self._client().messages.create(
                model=self.model,
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": user}],
            ),
            label="anthropic",
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        # Be tolerant of prose around the JSON.
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        return json.loads(match.group(1) if match else text)

    def generate_questions(self, *, mode, context_chunks, count, topic=None, tag=None, start_index=0):
        context = "\n\n---\n\n".join(context_chunks)
        kind = "behavioral/technical interview" if mode == PrepContext.INTERVIEW else "exam"
        user = (
            f"Source context:\n{context}\n\n"
            f"Generate {count} {kind} questions grounded strictly in the context above"
            f"{f' about {topic}' if topic else ''}. For each, return an object with "
            f'"question_text", "reference_answer", and "topic_or_category". '
            f"Return a JSON array."
        )
        return self._complete_json(GENERATION_SYSTEM_PROMPT, user)

    def grade_answer(self, *, question_text, reference_answer, submitted_answer, context=""):
        user = (
            f"Source context:\n{context}\n\n"
            f"Question: {question_text}\n"
            f"Reference/rubric: {reference_answer}\n"
            f"Candidate answer: {submitted_answer}\n\n"
            'Return JSON: {"score": 0-100, "feedback": "...", "missing_points": ["..."]}'
        )
        return self._complete_json(GRADING_SYSTEM_PROMPT, user)


class GeminiLLMClient(LLMClient):

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def _complete_json(self, system, user):
        from google import genai
        from google.genai import types

        from core.services.resilience import retry_call

        # Bounded HTTP timeout (ms) so a hung request can't wedge a worker.
        client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=30000))
        message = retry_call(
            lambda: client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                ),
            ),
            label="gemini",
        )
        text = message.text or ""
        # Be tolerant of any prose around the JSON, mirroring the Anthropic client.
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        return json.loads(match.group(1) if match else text)

    def generate_questions(self, *, mode, context_chunks, count, topic=None, tag=None, start_index=0):
        context = "\n\n---\n\n".join(context_chunks)
        kind = "behavioral/technical interview" if mode == PrepContext.INTERVIEW else "exam"
        user = (
            f"Source context:\n{context}\n\n"
            f"Generate {count} {kind} questions grounded strictly in the context above"
            f"{f' about {topic}' if topic else ''}. For each, return an object with "
            f'"question_text", "reference_answer", and "topic_or_category". '
            f"Return a JSON array."
        )
        return self._complete_json(GENERATION_SYSTEM_PROMPT, user)

    def grade_answer(self, *, question_text, reference_answer, submitted_answer, context=""):
        user = (
            f"Source context:\n{context}\n\n"
            f"Question: {question_text}\n"
            f"Reference/rubric: {reference_answer}\n"
            f"Candidate answer: {submitted_answer}\n\n"
            'Return JSON: {"score": 0-100, "feedback": "...", "missing_points": ["..."]}'
        )
        return self._complete_json(GRADING_SYSTEM_PROMPT, user)


def get_llm_client():
    if settings.LLM_PROVIDER == "anthropic":
        return AnthropicLLMClient(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL)
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLMClient(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    return FakeLLMClient()
