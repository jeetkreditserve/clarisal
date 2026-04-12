from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0005_alter_attendanceday_source_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendancepolicy',
            name='allowed_geo_sites',
            field=models.JSONField(
                blank=True,
                db_comment='DEPRECATED: historical geo-fence JSON; migrate to attendance_geo_fence_policies before removal.',
                default=list,
                help_text='DEPRECATED: Use GeoFencePolicy records tied to office locations.',
                null=True,
            ),
        ),
    ]
