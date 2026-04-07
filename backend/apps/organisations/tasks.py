from celery import shared_task

from .models import Organisation, TenantDataExportBatch
from .services import aggregate_org_usage_stat, generate_tenant_data_export_batch


@shared_task(name='organisations.aggregate_daily_usage_stats')
def aggregate_daily_usage_stats():
    processed = 0
    for organisation in Organisation.objects.all().iterator():
        aggregate_org_usage_stat(organisation)
        processed += 1
    return processed


@shared_task(name='organisations.generate_tenant_data_export')
def generate_tenant_data_export(batch_id):
    batch = TenantDataExportBatch.objects.get(id=batch_id)
    generate_tenant_data_export_batch(batch)
    return str(batch.id)
