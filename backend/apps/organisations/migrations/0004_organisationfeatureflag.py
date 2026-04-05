from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('organisations', '0003_actassession'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationFeatureFlag',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('feature_code', models.CharField(choices=[('ATTENDANCE', 'Attendance'), ('APPROVALS', 'Approvals'), ('BIOMETRICS', 'Biometric Devices'), ('NOTICES', 'Notices'), ('PAYROLL', 'Payroll'), ('PERFORMANCE', 'Performance'), ('RECRUITMENT', 'Recruitment'), ('REPORTS', 'Reports'), ('TIMEOFF', 'Leave and On-duty')], max_length=32)),
                ('is_enabled', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feature_flags', to='organisations.organisation')),
            ],
            options={
                'db_table': 'organisation_feature_flags',
                'ordering': ['feature_code'],
            },
        ),
        migrations.AddConstraint(
            model_name='organisationfeatureflag',
            constraint=models.UniqueConstraint(fields=('organisation', 'feature_code'), name='unique_feature_flag_per_org'),
        ),
    ]
