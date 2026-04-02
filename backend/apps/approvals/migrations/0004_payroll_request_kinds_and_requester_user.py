from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('approvals', '0003_expand_request_kind_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='approvalrun',
            name='requested_by_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='requested_approval_runs',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='approvalrun',
            name='requested_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='approval_runs',
                to='employees.employee',
            ),
        ),
        migrations.AlterField(
            model_name='approvalrun',
            name='request_kind',
            field=models.CharField(
                choices=[
                    ('LEAVE', 'Leave'),
                    ('ON_DUTY', 'On Duty'),
                    ('ATTENDANCE_REGULARIZATION', 'Attendance Regularization'),
                    ('PAYROLL_PROCESSING', 'Payroll Processing'),
                    ('SALARY_REVISION', 'Salary Revision'),
                    ('COMPENSATION_TEMPLATE_CHANGE', 'Compensation Template Change'),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='approvalworkflow',
            name='default_request_kind',
            field=models.CharField(
                blank=True,
                choices=[
                    ('LEAVE', 'Leave'),
                    ('ON_DUTY', 'On Duty'),
                    ('ATTENDANCE_REGULARIZATION', 'Attendance Regularization'),
                    ('PAYROLL_PROCESSING', 'Payroll Processing'),
                    ('SALARY_REVISION', 'Salary Revision'),
                    ('COMPENSATION_TEMPLATE_CHANGE', 'Compensation Template Change'),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='approvalworkflowrule',
            name='request_kind',
            field=models.CharField(
                choices=[
                    ('LEAVE', 'Leave'),
                    ('ON_DUTY', 'On Duty'),
                    ('ATTENDANCE_REGULARIZATION', 'Attendance Regularization'),
                    ('PAYROLL_PROCESSING', 'Payroll Processing'),
                    ('SALARY_REVISION', 'Salary Revision'),
                    ('COMPENSATION_TEMPLATE_CHANGE', 'Compensation Template Change'),
                ],
                max_length=32,
            ),
        ),
    ]

