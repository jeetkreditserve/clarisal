from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0004_add_probation_end_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeeprofile',
            name='esic_ip_number',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='employeeprofile',
            name='uan_number',
            field=models.CharField(blank=True, max_length=12),
        ),
    ]
