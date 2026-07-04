import logging

from core.services.embeddings import get_embedding_provider
from materials.constants import IngestionStatus
from materials.models import MaterialChunk
from tenants.constants import PrepContext

logger = logging.getLogger("prepcheck.materials")

CHUNK_WORDS = 180
CHUNK_OVERLAP = 30


def parse_source(material):
    if material.file:
        return _parse_pdf(material.file)
    if material.mode == PrepContext.INTERVIEW:
        return material.source_text or ""
    return material.source_text or ""


def _parse_pdf(file_field):
    from pypdf import PdfReader  # lazy: only needed for PDF uploads

    reader = PdfReader(file_field.open("rb"))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def chunk_text(text, size=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    step = max(1, size - overlap)
    while start < len(words):
        chunks.append(" ".join(words[start : start + size]))
        start += step
    return chunks


def ingest(material):
    material.ingestion_status = IngestionStatus.PROCESSING
    material.ingestion_error = ""
    material.save(update_fields=["ingestion_status", "ingestion_error", "updated_at"])
    logger.info(
        "Ingestion started",
        extra={"tenant": material.tenant_id, "user": material.uploaded_by_id},
    )

    try:
        text = parse_source(material)
        pieces = chunk_text(text)
        if not pieces:
            raise ValueError("No text could be extracted from the source material.")

        embedder = get_embedding_provider()
        vectors = embedder.embed(pieces)

        # Replace any prior chunks (re-ingest) then bulk-create the new ones.
        MaterialChunk.objects.filter(source_material=material).delete()
        MaterialChunk.objects.bulk_create(
            [
                MaterialChunk(
                    tenant=material.tenant,
                    source_material=material,
                    chunk_index=i,
                    chunk_text=piece,
                    embedding=vector,
                )
                for i, (piece, vector) in enumerate(zip(pieces, vectors))
            ]
        )

        material.ingestion_status = IngestionStatus.READY
        material.save(update_fields=["ingestion_status", "updated_at"])
        logger.info(
            "Ingestion complete: %s chunks",
            len(pieces),
            extra={"tenant": material.tenant_id, "user": material.uploaded_by_id},
        )
        return len(pieces)
    except Exception as exc:
        material.ingestion_status = IngestionStatus.FAILED
        material.ingestion_error = str(exc)
        material.save(update_fields=["ingestion_status", "ingestion_error", "updated_at"])
        logger.exception(
            "Ingestion failed", extra={"tenant": material.tenant_id, "user": material.uploaded_by_id}
        )
        raise
