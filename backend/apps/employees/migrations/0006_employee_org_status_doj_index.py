from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_employeeprofile_statutory_ids'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(
                fields=['organisation', 'status', 'date_of_joining'],
                name='employee_org_status_doj_idx',
            ),
        ),
    ]
