from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organisations', '0002_organisation_tan_number'),
        ('payroll', '0012_statutoryfilingbatch'),
    ]

    operations = [
        migrations.CreateModel(
            name='PayrollTDSChallan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('fiscal_year', models.CharField(max_length=16)),
                ('quarter', models.CharField(choices=[('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')], max_length=2)),
                ('period_year', models.PositiveIntegerField()),
                ('period_month', models.PositiveIntegerField()),
                ('bsr_code', models.CharField(max_length=7)),
                ('challan_serial_number', models.CharField(max_length=16)),
                ('deposit_date', models.DateField()),
                ('tax_deposited', models.DecimalField(decimal_places=2, max_digits=12)),
                ('interest_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('fee_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('statement_receipt_number', models.CharField(blank=True, max_length=32)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payroll_tds_challans', to='organisations.organisation')),
            ],
            options={
                'db_table': 'payroll_tds_challans',
                'ordering': ['fiscal_year', 'period_year', 'period_month', 'deposit_date'],
            },
        ),
        migrations.AddConstraint(
            model_name='payrolltdschallan',
            constraint=models.UniqueConstraint(fields=('organisation', 'period_year', 'period_month'), name='unique_payroll_tds_challan_per_org_period'),
        ),
        migrations.AddIndex(
            model_name='payrolltdschallan',
            index=models.Index(fields=['organisation', 'fiscal_year', 'quarter'], name='payroll_tds_organis_882124_idx'),
        ),
        migrations.AddIndex(
            model_name='payrolltdschallan',
            index=models.Index(fields=['organisation', 'period_year', 'period_month'], name='payroll_tds_organis_8b2777_idx'),
        ),
    ]
