import logging

try:
    import structlog
except ImportError:  # pragma: no cover - optional dependency in dev images
    structlog = None
from celery import shared_task

from .models import Organisation, TenantDataExportBatch
from .services import aggregate_org_usage_stat, generate_tenant_data_export_batch

logger = structlog.get_logger(__name__) if structlog is not None else logging.getLogger(__name__)


@shared_task(name='organisations.aggregate_daily_usage_stats')
def aggregate_daily_usage_stats():
    processed = 0
    for organisation in Organisation.objects.all().iterator():
        aggregate_org_usage_stat(organisation)
        processed += 1
    logger.info("aggregate_daily_usage_stats.done", organisations_processed=processed)
    return processed


@shared_task(name='organisations.generate_tenant_data_export')
def generate_tenant_data_export(batch_id):
    batch = TenantDataExportBatch.objects.get(id=batch_id)
    generate_tenant_data_export_batch(batch)
    logger.info("generate_tenant_data_export.done", batch_id=str(batch.id))
    return str(batch.id)
