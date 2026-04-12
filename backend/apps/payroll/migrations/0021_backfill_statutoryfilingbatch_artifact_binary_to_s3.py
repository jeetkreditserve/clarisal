from __future__ import annotations

from io import BytesIO

from django.db import migrations
from django.utils import timezone


def backfill_artifact_binary_to_s3(apps, schema_editor):
    from apps.documents.s3 import upload_file

    StatutoryFilingBatch = apps.get_model("payroll", "StatutoryFilingBatch")

    queryset = StatutoryFilingBatch.objects.exclude(artifact_binary__isnull=True).iterator()
    for batch in queryset:
        payload = bytes(batch.artifact_binary or b"")
        if not payload or batch.artifact_storage_key:
            continue

        safe_file_name = (batch.file_name or "statutory-filing").replace("/", "-")
        artifact_storage_key = f"payroll/filings/{batch.organisation_id}/{batch.id}/{safe_file_name}"
        upload_file(
            BytesIO(payload),
            artifact_storage_key,
            batch.content_type or "application/octet-stream",
        )
        batch.artifact_storage_backend = "s3"
        batch.artifact_storage_key = artifact_storage_key
        batch.artifact_uploaded_at = batch.artifact_uploaded_at or timezone.now()
        batch.file_size_bytes = batch.file_size_bytes or len(payload)
        batch.save(
            update_fields=[
                "artifact_storage_backend",
                "artifact_storage_key",
                "artifact_uploaded_at",
                "file_size_bytes",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0020_statutoryfilingbatch_artifact_storage_backend_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_artifact_binary_to_s3, migrations.RunPython.noop),
    ]
