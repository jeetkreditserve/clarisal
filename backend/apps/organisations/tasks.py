import logging
from types import ModuleType
from typing import Any

from celery import shared_task

from .models import Organisation, Payment, TenantDataExportBatch
from .services import (
    aggregate_org_usage_stat,
    generate_invoice,
    generate_tenant_data_export_batch,
    process_payment_webhook,
    process_razorpay_webhook,
)

structlog_module: ModuleType | None
try:
    import structlog as structlog_module
except ImportError:  # pragma: no cover - optional dependency in dev images
    structlog_module = None

logger: Any = structlog_module.get_logger(__name__) if structlog_module is not None else logging.getLogger(__name__)


@shared_task(name='organisations.aggregate_daily_usage_stats')
def aggregate_daily_usage_stats():
    processed = 0
    for organisation in Organisation.objects.order_by('created_at', 'id').iterator():
        try:
            aggregate_org_usage_stat(organisation)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "usage_stats_aggregation_failed",
                extra={
                    "org_id": str(organisation.id),
                    "org_name": organisation.name,
                    "error": str(exc),
                },
            )
        finally:
            processed += 1
    logger.info("aggregate_daily_usage_stats.done", organisations_processed=processed)
    return processed


@shared_task(
    name='organisations.generate_tenant_data_export',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def generate_tenant_data_export(self, batch_id):
    batch = TenantDataExportBatch.objects.get(id=batch_id)
    try:
        generate_tenant_data_export_batch(batch, raise_on_failure=True)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "generate_tenant_data_export.failed",
            extra={"batch_id": str(batch.id), "attempt": self.request.retries + 1, "error": str(exc)},
        )
        raise
    logger.info("generate_tenant_data_export.done", batch_id=str(batch.id))
    return str(batch.id)


@shared_task(
    name='organisations.generate_invoice',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def generate_invoice_task(self, payment_id):
    payment = Payment.objects.get(id=payment_id)
    invoice = generate_invoice(payment)
    logger.info("generate_invoice.done", payment_id=str(payment.id), invoice_id=str(invoice.id))
    return str(invoice.id)


@shared_task(
    name='organisations.process_payment_webhook',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_payment_webhook_task(self, payload, signature, gateway_name):
    result = process_payment_webhook(payload.encode('utf-8'), signature, gateway_name)
    logger.info("process_payment_webhook.done", gateway=gateway_name, status=result.get('status'))
    return result


@shared_task(
    name='organisations.process_razorpay_webhook',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_razorpay_webhook_task(self, payload, signature):
    billing_event = process_razorpay_webhook(payload.encode('utf-8'), signature)
    logger.info(
        "process_razorpay_webhook.done",
        provider_event_id=billing_event.provider_event_id,
        status=billing_event.status,
    )
    return str(billing_event.id)
