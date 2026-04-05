from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('organisations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0004_add_probation_end_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppraisalCycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('review_type', models.CharField(choices=[('SELF', 'Self Review'), ('MANAGER', 'Manager Review'), ('360', '360° Review')], default='SELF', max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ACTIVE', 'Active'), ('CLOSED', 'Closed')], default='DRAFT', max_length=20)),
                ('is_probation_review', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appraisal_cycles', to='organisations.organisation')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GoalCycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ACTIVE', 'Active'), ('CLOSED', 'Closed')], default='DRAFT', max_length=20)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goal_cycles', to='organisations.organisation')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=300)),
                ('description', models.TextField(blank=True)),
                ('target', models.TextField(blank=True, help_text='Measurable target / key result')),
                ('metric', models.CharField(blank=True, help_text='Unit of measurement', max_length=100)),
                ('weight', models.DecimalField(decimal_places=2, default=1, max_digits=5)),
                ('status', models.CharField(choices=[('NOT_STARTED', 'Not Started'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], default='NOT_STARTED', max_length=20)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('progress_percent', models.PositiveSmallIntegerField(default=0)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goals', to='performance.goalcycle')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goals', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FeedbackRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('REQUESTED', 'Requested'), ('SUBMITTED', 'Submitted'), ('DECLINED', 'Declined')], default='REQUESTED', max_length=20)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('message', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback_requests', to='performance.appraisalcycle')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback_requests_received', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('requested_from', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback_requests_to_give', to='employees.employee')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AppraisalReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('relationship', models.CharField(choices=[('SELF', 'Self'), ('MANAGER', 'Manager'), ('PEER', 'Peer'), ('SKIP_LEVEL', 'Skip Level'), ('DIRECT_REPORT', 'Direct Report')], max_length=20)),
                ('ratings', models.JSONField(default=dict, help_text='{"competency_id": rating_score, ...}')),
                ('comments', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('SUBMITTED', 'Submitted'), ('ACKNOWLEDGED', 'Acknowledged')], default='PENDING', max_length=20)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='performance.appraisalcycle')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appraisal_reviews', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('reviewer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reviews_given', to='employees.employee')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='goalcycle',
            index=models.Index(fields=['organisation', 'status'], name='performance_organis_4070c9_idx'),
        ),
        migrations.AddIndex(
            model_name='goalcycle',
            index=models.Index(fields=['organisation', 'start_date', 'end_date'], name='performance_organis_fced44_idx'),
        ),
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['employee', 'status'], name='performance_employe_6b4f4f_idx'),
        ),
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['cycle', 'employee'], name='performance_cycle_i_edd875_idx'),
        ),
        migrations.AddIndex(
            model_name='feedbackrequest',
            index=models.Index(fields=['cycle', 'status'], name='performance_cycle_i_fb051e_idx'),
        ),
        migrations.AddIndex(
            model_name='feedbackrequest',
            index=models.Index(fields=['requested_from', 'status'], name='performance_request_be1f2f_idx'),
        ),
        migrations.AddIndex(
            model_name='appraisalreview',
            index=models.Index(fields=['cycle', 'employee'], name='performance_cycle_i_10947f_idx'),
        ),
        migrations.AddIndex(
            model_name='appraisalreview',
            index=models.Index(fields=['reviewer', 'status'], name='performance_reviewe_9321e9_idx'),
        ),
        migrations.AddConstraint(
            model_name='appraisalreview',
            constraint=models.UniqueConstraint(
                fields=('cycle', 'employee', 'reviewer', 'relationship'),
                name='unique_appraisal_review_per_cycle_employee_reviewer_relationship',
            ),
        ),
        migrations.AddIndex(
            model_name='appraisalcycle',
            index=models.Index(fields=['organisation', 'status'], name='performance_organis_b68999_idx'),
        ),
        migrations.AddIndex(
            model_name='appraisalcycle',
            index=models.Index(fields=['organisation', 'is_probation_review'], name='performance_organis_bff001_idx'),
        ),
    ]
