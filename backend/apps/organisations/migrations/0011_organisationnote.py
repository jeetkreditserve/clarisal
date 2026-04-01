from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organisations', '0010_organisationbootstrapadmin_contact_links'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationNote',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organisation_notes', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='organisations.organisation')),
            ],
            options={
                'db_table': 'organisation_notes',
                'ordering': ['-created_at'],
            },
        ),
    ]
