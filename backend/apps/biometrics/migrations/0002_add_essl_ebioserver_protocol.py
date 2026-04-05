from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('biometrics', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='biometricdevice',
            name='protocol',
            field=models.CharField(
                choices=[
                    ('ZK_ADMS', 'ZKTeco / eSSL / Biomax (ADMS Push)'),
                    ('ESSL_EBIOSERVER', 'eSSL eBioserver (Webhook Push)'),
                    ('MATRIX_COSEC', 'Matrix COSEC (REST Pull)'),
                    ('SUPREMA_BIOSTAR', 'Suprema BioStar 2 (REST Pull)'),
                    ('HIKVISION_ISAPI', 'HikVision ISAPI (REST Pull)'),
                ],
                max_length=30,
            ),
        ),
    ]
