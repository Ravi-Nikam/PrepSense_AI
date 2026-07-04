import pytest

from core.services.embeddings import get_embedding_provider
from core.services.retrieval import DEFAULT_TOP_K, top_k_chunks
from materials.models import MaterialChunk
from tenants.context import tenant_context

pytestmark = pytest.mark.django_db


def _add_chunks(material, texts):
    vecs = get_embedding_provider().embed(texts)
    for i, (text, vec) in enumerate(zip(texts, vecs)):
        MaterialChunk.objects.create(
            source_material=material, chunk_index=i, chunk_text=text, embedding=vec
        )


def test_small_material_returns_all_chunks(org_a, make_material):
    material = make_material(org_a)
    with tenant_context(org_a):
        _add_chunks(material, [f"chunk {i}" for i in range(5)])
        result = top_k_chunks(material, "anything", k=DEFAULT_TOP_K)
    assert len(result) == 5  # <= K -> use everything


def test_large_material_selects_top_k_most_similar(org_a, make_material):
    material = make_material(org_a)
    query = "rate limiter token bucket design"
    # 3 chunks identical to the query (fake embeddings collide) must rank top.
    texts = [query if i < 3 else f"unrelated passage {i}" for i in range(20)]
    with tenant_context(org_a):
        _add_chunks(material, texts)
        result = top_k_chunks(material, query, k=5)
    assert len(result) == 5
    assert [c.chunk_text for c in result].count(query) == 3
    # Reading order preserved (ascending chunk_index).
    assert result == sorted(result, key=lambda c: c.chunk_index)
