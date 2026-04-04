from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='tan_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
