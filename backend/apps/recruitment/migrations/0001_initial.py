from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('departments', '0001_initial'),
        ('organisations', '0001_initial'),
        ('locations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0004_add_probation_end_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('stage', models.CharField(choices=[('APPLIED', 'Applied'), ('SCREENING', 'Screening'), ('INTERVIEW', 'Interview'), ('OFFER', 'Offer'), ('HIRED', 'Hired'), ('REJECTED', 'Rejected'), ('WITHDRAWN', 'Withdrawn')], default='APPLIED', max_length=20)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-applied_at'],
            },
        ),
        migrations.CreateModel(
            name='JobPosting',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('requirements', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('OPEN', 'Open'), ('PAUSED', 'Paused'), ('CLOSED', 'Closed'), ('FILLED', 'Filled')], default='DRAFT', max_length=20)),
                ('posted_at', models.DateTimeField(blank=True, null=True)),
                ('closes_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_postings', to='departments.department')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_postings', to='locations.officelocation')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_postings', to='organisations.organisation')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('scheduled_at', models.DateTimeField()),
                ('format', models.CharField(choices=[('PHONE', 'Phone'), ('VIDEO', 'Video'), ('IN_PERSON', 'In Person'), ('TECHNICAL', 'Technical')], default='VIDEO', max_length=20)),
                ('feedback', models.TextField(blank=True)),
                ('outcome', models.CharField(choices=[('PENDING', 'Pending'), ('PASSED', 'Passed'), ('FAILED', 'Failed'), ('NO_SHOW', 'No Show')], default='PENDING', max_length=20)),
                ('meet_link', models.URLField(blank=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interviews', to='recruitment.application')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('interviewer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interviews_conducted', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['scheduled_at'],
            },
        ),
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('resume_file_key', models.CharField(blank=True, help_text='S3 object key', max_length=500)),
                ('source', models.CharField(blank=True, help_text='LinkedIn, Naukri, Referral, etc.', max_length=100)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidates', to='organisations.organisation')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='application',
            name='candidate',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='recruitment.candidate'),
        ),
        migrations.AddField(
            model_name='application',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='application',
            name='job_posting',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='recruitment.jobposting'),
        ),
        migrations.AddField(
            model_name='application',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='OfferLetter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('ctc_annual', models.DecimalField(decimal_places=2, max_digits=14)),
                ('joining_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SENT', 'Sent'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined'), ('EXPIRED', 'Expired'), ('REVOKED', 'Revoked')], default='DRAFT', max_length=20)),
                ('template_text', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='offer_letter', to='recruitment.application')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('onboarded_employee', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offer_letter', to='employees.employee')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['status', 'expires_at'], name='recruitment_status_967a1b_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='jobposting',
            index=models.Index(fields=['organisation', 'status'], name='recruitment_organis_b6bb74_idx'),
        ),
        migrations.AddIndex(
            model_name='jobposting',
            index=models.Index(fields=['organisation', 'posted_at'], name='recruitment_organis_592948_idx'),
        ),
        migrations.AddIndex(
            model_name='interview',
            index=models.Index(fields=['application', 'scheduled_at'], name='recruitment_applica_45607c_idx'),
        ),
        migrations.AddIndex(
            model_name='interview',
            index=models.Index(fields=['interviewer', 'scheduled_at'], name='recruitment_intervi_72e1da_idx'),
        ),
        migrations.AddIndex(
            model_name='candidate',
            index=models.Index(fields=['organisation', 'email'], name='recruitment_organis_089c5f_idx'),
        ),
        migrations.AddConstraint(
            model_name='candidate',
            constraint=models.UniqueConstraint(fields=('organisation', 'email'), name='unique_candidate_email_per_org'),
        ),
        migrations.AddIndex(
            model_name='application',
            index=models.Index(fields=['job_posting', 'stage'], name='recruitment_job_pos_86b6d7_idx'),
        ),
        migrations.AddIndex(
            model_name='application',
            index=models.Index(fields=['candidate', 'stage'], name='recruitment_candida_c12cf4_idx'),
        ),
        migrations.AddConstraint(
            model_name='application',
            constraint=models.UniqueConstraint(fields=('candidate', 'job_posting'), name='unique_candidate_job_application'),
        ),
    ]
