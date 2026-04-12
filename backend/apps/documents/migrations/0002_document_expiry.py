from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='alert_days_before',
            field=models.PositiveSmallIntegerField(
                default=30,
                help_text='Days before expiry_date when the owner should be alerted.',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='expiry_date',
            field=models.DateField(
                blank=True,
                help_text='Date after which this document is no longer valid. Null means the document does not expire.',
                null=True,
            ),
        ),
    ]
