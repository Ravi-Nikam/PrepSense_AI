import hashlib
import math

from django.conf import settings


class EmbeddingProvider:
    dim = 0

    def embed(self, texts):
        raise NotImplementedError

    def embed_one(self, text):
        return self.embed([text])[0]


class FakeEmbeddingProvider(EmbeddingProvider):

    def __init__(self, dim):
        self.dim = dim

    def embed(self, texts):
        return [self._vector(t) for t in texts]

    def _vector(self, text):
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vals = []
        counter = 0
        while len(vals) < self.dim:
            block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for byte in block:
                vals.append((byte / 255.0) * 2.0 - 1.0)  # in [-1, 1]
                if len(vals) >= self.dim:
                    break
            counter += 1
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


class VoyageEmbeddingProvider(EmbeddingProvider):

    def __init__(self, dim, model, api_key):
        self.dim = dim
        self.model = model
        self.api_key = api_key

    def embed(self, texts):
        import voyageai

        from core.services.resilience import retry_call

        client = voyageai.Client(api_key=self.api_key)
        result = retry_call(
            lambda: client.embed(list(texts), model=self.model),
            label="voyage",
        )
        return result.embeddings


def get_embedding_provider():
    if settings.EMBEDDING_PROVIDER == "voyage":
        return VoyageEmbeddingProvider(
            settings.EMBEDDING_DIM,
            settings.ANTHROPIC_EMBEDDING_MODEL,
            settings.VOYAGE_API_KEY,
        )
    return FakeEmbeddingProvider(settings.EMBEDDING_DIM)


def cosine_similarity(a, b):
    if a is None or b is None:
        return 0.0
    a = list(a)
    b = list(b)
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def is_duplicate(candidate_vec, existing_vecs, threshold=0.95):
    return any(cosine_similarity(candidate_vec, v) >= threshold for v in existing_vecs)
