from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0003_employee_offboarding'),
        ('payroll', '0004_add_old_regime_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvestmentDeclaration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('fiscal_year', models.CharField(max_length=16)),
                ('section', models.CharField(choices=[('80C', 'Section 80C'), ('80D', 'Section 80D'), ('80TTA', 'Section 80TTA'), ('80G', 'Section 80G'), ('HRA', 'House Rent Allowance'), ('LTA', 'Leave Travel Allowance'), ('OTHER', 'Other')], max_length=10)),
                ('description', models.CharField(max_length=200)),
                ('declared_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('proof_file_key', models.CharField(blank=True, max_length=500, null=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investment_declarations', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_investment_declarations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'investment_declarations',
                'ordering': ['section', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='investmentdeclaration',
            index=models.Index(fields=['employee', 'fiscal_year'], name='investment__employe_8eb3e8_idx'),
        ),
    ]
