from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0021_backfill_statutoryfilingbatch_artifact_binary_to_s3"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="statutoryfilingbatch",
            name="artifact_binary",
        ),
    ]
