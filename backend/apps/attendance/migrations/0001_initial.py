from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0002_employee_approval_workflows'),
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceImportJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('mode', models.CharField(choices=[('ATTENDANCE_SHEET', 'Attendance Sheet'), ('PUNCH_SHEET', 'Punch Sheet')], max_length=32)),
                ('status', models.CharField(choices=[('FAILED', 'Failed'), ('READY_FOR_REVIEW', 'Ready For Review'), ('POSTED', 'Posted')], max_length=24)),
                ('original_filename', models.CharField(max_length=255)),
                ('total_rows', models.PositiveIntegerField(default=0)),
                ('valid_rows', models.PositiveIntegerField(default=0)),
                ('error_rows', models.PositiveIntegerField(default=0)),
                ('posted_rows', models.PositiveIntegerField(default=0)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_import_jobs', to='organisations.organisation')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_attendance_import_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'attendance_import_jobs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('attendance_date', models.DateField()),
                ('check_in_at', models.DateTimeField()),
                ('check_out_at', models.DateTimeField(blank=True, null=True)),
                ('source', models.CharField(choices=[('EXCEL_IMPORT', 'Excel Import')], default='EXCEL_IMPORT', max_length=24)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='employees.employee')),
                ('import_job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='attendance.attendanceimportjob')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='organisations.organisation')),
            ],
            options={
                'db_table': 'attendance_records',
                'ordering': ['-attendance_date', 'employee__employee_code'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceImportRow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('row_number', models.PositiveIntegerField()),
                ('employee_code', models.CharField(blank=True, max_length=20)),
                ('attendance_date', models.DateField(blank=True, null=True)),
                ('check_in_at', models.DateTimeField(blank=True, null=True)),
                ('check_out_at', models.DateTimeField(blank=True, null=True)),
                ('raw_punch_times', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('VALID', 'Valid'), ('ERROR', 'Error'), ('INCOMPLETE', 'Incomplete'), ('POSTED', 'Posted')], max_length=16)),
                ('error_message', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='employees.employee')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='attendance.attendanceimportjob')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'attendance_import_rows',
                'ordering': ['row_number', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='attendanceimportjob',
            index=models.Index(fields=['organisation', 'mode', 'status'], name='attendance_i_organis_1bc4ba_idx'),
        ),
        migrations.AddIndex(
            model_name='attendanceimportjob',
            index=models.Index(fields=['organisation', 'created_at'], name='attendance_i_organis_3f1e3e_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['organisation', 'attendance_date'], name='attendance_r_organis_f7f67e_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['employee', 'attendance_date'], name='attendance_r_employe_29a743_idx'),
        ),
        migrations.AddConstraint(
            model_name='attendancerecord',
            constraint=models.UniqueConstraint(fields=('organisation', 'employee', 'attendance_date'), name='unique_attendance_record_per_employee_day'),
        ),
        migrations.AddIndex(
            model_name='attendanceimportrow',
            index=models.Index(fields=['job', 'status'], name='attendance_i_job_id_31e37b_idx'),
        ),
        migrations.AddIndex(
            model_name='attendanceimportrow',
            index=models.Index(fields=['employee', 'attendance_date'], name='attendance_i_employe_2c24b9_idx'),
        ),
    ]
