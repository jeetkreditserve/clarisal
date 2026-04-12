from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('performance', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='appraisalcycle',
            name='activated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='calibration_deadline',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='goal_cycle',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='appraisal_cycles',
                to='performance.goalcycle',
            ),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='manager_review_deadline',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='peer_review_deadline',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appraisalcycle',
            name='self_assessment_deadline',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='goalcycle',
            name='auto_create_review_cycle',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='appraisalcycle',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('ACTIVE', 'Active'),
                    ('SELF_ASSESSMENT', 'Self Assessment'),
                    ('PEER_REVIEW', 'Peer Review'),
                    ('MANAGER_REVIEW', 'Manager Review'),
                    ('CALIBRATION', 'Calibration'),
                    ('COMPLETED', 'Completed'),
                    ('CLOSED', 'Closed'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='goalcycle',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('ACTIVE', 'Active'),
                    ('SELF_ASSESSMENT', 'Self Assessment'),
                    ('PEER_REVIEW', 'Peer Review'),
                    ('MANAGER_REVIEW', 'Manager Review'),
                    ('CALIBRATION', 'Calibration'),
                    ('COMPLETED', 'Completed'),
                    ('CLOSED', 'Closed'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='CalibrationSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('locked_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('cycle', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='calibration_session', to='performance.appraisalcycle')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FeedbackResponse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('ratings', models.JSONField(default=dict, help_text='{"competency_id": rating_score, ...}')),
                ('comments', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='response', to='performance.feedbackrequest')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='feedbackresponse',
            index=models.Index(fields=['submitted_at'], name='performance_submitte_338f0d_idx'),
        ),
        migrations.CreateModel(
            name='CalibrationSessionEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('original_rating', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('current_rating', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('reason', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calibration_entries', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='performance.calibrationsession')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='calibrationsessionentry',
            index=models.Index(fields=['session', 'employee'], name='performance_session_54d2b3_idx'),
        ),
        migrations.AddConstraint(
            model_name='calibrationsessionentry',
            constraint=models.UniqueConstraint(fields=('session', 'employee'), name='unique_calibration_entry_per_session_employee'),
        ),
    ]
