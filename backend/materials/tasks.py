import logging

from celery import shared_task

from tenants.context import tenant_context

logger = logging.getLogger("prepcheck.materials")


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def ingest_material_task(self, material_id, tenant_id):
    from materials.models import SourceMaterial
    from materials.services.ingestion import ingest
    from tenants.models import Organization

    org = Organization.objects.filter(id=tenant_id).first()
    if org is None:
        logger.error("ingest_material_task: unknown tenant %s", tenant_id)
        return

    with tenant_context(org):
        material = SourceMaterial.objects.filter(id=material_id).first()
        if material is None:
            logger.error("ingest_material_task: material %s not in tenant %s", material_id, tenant_id)
            return
        return ingest(material)
