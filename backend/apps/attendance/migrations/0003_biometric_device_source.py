from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0002_full_attendance_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendancepunch',
            name='source',
            field=models.CharField(
                choices=[
                    ('WEB', 'Web'),
                    ('IMPORT', 'Excel Import'),
                    ('API', 'External API'),
                    ('DEVICE', 'Biometric Device'),
                    ('REGULARIZATION', 'Regularization'),
                    ('MANUAL', 'Manual'),
                ],
                default='WEB',
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name='attendanceday',
            name='source',
            field=models.CharField(
                blank=True,
                choices=[
                    ('WEB', 'Web'),
                    ('IMPORT', 'Excel Import'),
                    ('API', 'External API'),
                    ('DEVICE', 'Biometric Device'),
                    ('REGULARIZATION', 'Regularization'),
                    ('MANUAL', 'Manual'),
                ],
                default='',
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='source',
            field=models.CharField(
                choices=[
                    ('EXCEL_IMPORT', 'Excel Import'),
                    ('MANUAL_OVERRIDE', 'Manual Override'),
                    ('REGULARIZATION', 'Regularization'),
                ],
                default='EXCEL_IMPORT',
                max_length=24,
            ),
        ),
    ]
