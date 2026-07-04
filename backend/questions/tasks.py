import logging

from celery import shared_task

from tenants.context import tenant_context

logger = logging.getLogger("prepcheck.questions")


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generate_questions_task(self, material_id, tenant_id, count=5, difficulty=None, category=None):
    from materials.models import SourceMaterial
    from questions.services.generation import generate_paper
    from tenants.models import Organization

    org = Organization.objects.filter(id=tenant_id).first()
    if org is None:
        logger.error("generate_questions_task: unknown tenant %s", tenant_id)
        return 0

    with tenant_context(org):
        material = SourceMaterial.objects.filter(id=material_id).first()
        if material is None or not material.is_ready:
            logger.error(
                "generate_questions_task: material %s not ready in tenant %s", material_id, tenant_id
            )
            return 0
        # Build a full paper (batched + deduped) up to the requested count.
        created = generate_paper(
            material, target=count, difficulty=difficulty, category=category
        )
        return len(created)
