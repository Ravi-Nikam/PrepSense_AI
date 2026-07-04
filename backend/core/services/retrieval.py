"""Top-K chunk retrieval for grounding LLM calls.

Ranks a material's chunks by embedding cosine-similarity to a query and returns the
most relevant K. Falls back to all chunks when the material is small or embeddings
are unavailable, so grounding never breaks — a thin source still uses everything,
while a large one feeds the LLM only the passages that matter (context + cost).
"""
from core.services.embeddings import cosine_similarity, get_embedding_provider

DEFAULT_TOP_K = 12


def top_k_chunks(material, query_text, k=DEFAULT_TOP_K):
    chunks = list(material.chunks.all().order_by("chunk_index"))
    if len(chunks) <= k or not query_text:
        return chunks

    with_vecs = [c for c in chunks if c.embedding is not None]
    if len(with_vecs) <= k:
        return chunks

    query_vec = get_embedding_provider().embed_one(query_text)
    ranked = sorted(
        with_vecs,
        key=lambda c: cosine_similarity(query_vec, c.embedding),
        reverse=True,
    )[:k]
    # Preserve reading order so the LLM sees coherent, sequential context.
    ranked.sort(key=lambda c: c.chunk_index)
    return ranked
