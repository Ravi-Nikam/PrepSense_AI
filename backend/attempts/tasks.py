import logging

from celery import shared_task

from tenants.context import tenant_context

logger = logging.getLogger("prepcheck.attempts")


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def grade_attempt_task(self, attempt_id, tenant_id):
    from attempts.models import Attempt
    from attempts.services.grading import grade
    from tenants.models import Organization

    org = Organization.objects.filter(id=tenant_id).first()
    if org is None:
        logger.error("grade_attempt_task: unknown tenant %s", tenant_id)
        return

    with tenant_context(org):
        attempt = Attempt.objects.filter(id=attempt_id).first()
        if attempt is None:
            logger.error("grade_attempt_task: attempt %s not in tenant %s", attempt_id, tenant_id)
            return
        return grade(attempt)
