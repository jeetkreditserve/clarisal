from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0003_employee_offboarding'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='probation_end_date',
            field=models.DateField(
                blank=True,
                help_text='Date on which the employee completes their probation period.',
                null=True,
            ),
        ),
    ]
