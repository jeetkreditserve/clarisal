from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0022_remove_statutoryfilingbatch_artifact_binary'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrunitem',
            name='epf_employer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrunitem',
            name='eps_employer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
    ]
