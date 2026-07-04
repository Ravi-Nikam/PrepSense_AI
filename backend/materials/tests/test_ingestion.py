import pytest

from accounts.constants import Role
from materials.constants import IngestionStatus
from materials.models import MaterialChunk, SourceMaterial
from materials.services.ingestion import chunk_text
from tenants.constants import PrepContext

pytestmark = pytest.mark.django_db


def test_chunk_text_overlaps_and_covers():
    words = " ".join(f"w{i}" for i in range(400))
    chunks = chunk_text(words, size=180, overlap=30)
    assert len(chunks) >= 2
    # Overlap: end of chunk 0 reappears at the start of chunk 1.
    assert chunks[0].split()[-1] in chunks[1].split()


def test_upload_triggers_ingestion_and_creates_embedded_chunks(org_a, make_user, auth_client):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    long_jd = "We need a backend engineer. " * 60  # enough words to chunk

    resp = auth_client(teacher).post(
        "/api/materials/",
        {"mode": PrepContext.INTERVIEW, "subject_or_role": "Backend Engineer", "source_text": long_jd},
        format="json",
    )
    assert resp.status_code == 201
    material_id = resp.json()["data"]["id"]

    material = SourceMaterial.all_objects.get(id=material_id)
    assert material.ingestion_status == IngestionStatus.READY

    chunks = MaterialChunk.all_objects.filter(source_material_id=material_id)
    assert chunks.count() >= 1
    # Every chunk is embedded and stamped with the material's tenant.
    for c in chunks:
        assert c.tenant_id == org_a.id
        assert c.embedding is not None and len(c.embedding) == 1024


def test_ingestion_marks_failed_when_no_text(org_a, make_user, auth_client, monkeypatch):
    teacher = make_user(org_a, role=Role.MENTOR, email="m@a.com")
    from materials.services import ingestion

    monkeypatch.setattr(ingestion, "parse_source", lambda material: "")

    resp = auth_client(teacher).post(
        "/api/materials/",
        {"mode": PrepContext.INTERVIEW, "subject_or_role": "Role", "source_text": "something"},
        format="json",
    )
    # Upload succeeds; ingestion (eager) fails and marks the row FAILED.
    material = SourceMaterial.all_objects.get(id=resp.json()["data"]["id"])
    assert material.ingestion_status == IngestionStatus.FAILED
    assert material.ingestion_error
