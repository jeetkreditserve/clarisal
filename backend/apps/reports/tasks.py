from celery import shared_task
from django.utils import timezone

from .exporters import build_export
from .models import ReportRun
from .query_engine import preview_report


@shared_task
def run_report_task(run_id, file_format='xlsx'):
    run = ReportRun.objects.select_related('template', 'organisation', 'requested_by').get(id=run_id)
    run.status = ReportRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at', 'modified_at'])
    try:
        result = preview_report(run.template, run.requested_by, run.organisation, limit=50000, parameters=run.parameters)
        export = build_export(run, result, file_format)
        run.status = ReportRun.Status.SUCCEEDED
        run.row_count = len(result['rows'])
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'row_count', 'completed_at', 'modified_at'])
        return {'run_id': str(run.id), 'export_id': str(export.id)}
    except Exception as exc:
        run.status = ReportRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at', 'modified_at'])
        raise
