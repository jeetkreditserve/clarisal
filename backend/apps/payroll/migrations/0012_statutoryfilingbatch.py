from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organisations', '0001_initial'),
        ('payroll', '0011_payslip_esi_contribution_period_end_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatutoryFilingBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('filing_type', models.CharField(choices=[('PF_ECR', 'PF ECR'), ('ESI_MONTHLY', 'ESI Monthly'), ('FORM24Q', 'Form 24Q'), ('PROFESSIONAL_TAX', 'Professional Tax'), ('FORM16', 'Form 16')], max_length=32)),
                ('status', models.CharField(choices=[('READY', 'Ready'), ('BLOCKED', 'Blocked'), ('GENERATED', 'Generated'), ('SUPERSEDED', 'Superseded'), ('CANCELLED', 'Cancelled')], default='READY', max_length=16)),
                ('artifact_format', models.CharField(choices=[('CSV', 'CSV'), ('JSON', 'JSON'), ('XML', 'XML'), ('PDF', 'PDF'), ('TEXT', 'Text')], default='CSV', max_length=16)),
                ('period_year', models.PositiveIntegerField(blank=True, null=True)),
                ('period_month', models.PositiveIntegerField(blank=True, null=True)),
                ('fiscal_year', models.CharField(blank=True, max_length=16)),
                ('quarter', models.CharField(blank=True, max_length=2)),
                ('checksum', models.CharField(blank=True, max_length=64)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=120)),
                ('file_size_bytes', models.PositiveIntegerField(default=0)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('source_signature', models.CharField(blank=True, max_length=64)),
                ('validation_errors', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('structured_payload', models.JSONField(blank=True, default=dict)),
                ('artifact_text', models.TextField(blank=True)),
                ('artifact_binary', models.BinaryField(blank=True, null=True)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='statutory_filing_batches', to='organisations.organisation')),
                ('source_pay_runs', models.ManyToManyField(blank=True, related_name='statutory_filing_batches', to='payroll.payrollrun')),
            ],
            options={
                'db_table': 'statutory_filing_batches',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='statutoryfilingbatch',
            index=models.Index(fields=['organisation', 'filing_type', 'status'], name='statutory_f_org_id_5fad0a_idx'),
        ),
        migrations.AddIndex(
            model_name='statutoryfilingbatch',
            index=models.Index(fields=['organisation', 'period_year', 'period_month'], name='statutory_f_org_id_0d474b_idx'),
        ),
        migrations.AddIndex(
            model_name='statutoryfilingbatch',
            index=models.Index(fields=['organisation', 'fiscal_year', 'quarter'], name='statutory_f_org_id_e1fe70_idx'),
        ),
    ]
