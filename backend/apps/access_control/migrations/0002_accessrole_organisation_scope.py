# Generated manually for P38 access-role scoping.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('access_control', '0001_initial'),
        ('organisations', '0008_billing_payment_invoice'),
    ]

    operations = [
        migrations.AddField(
            model_name='accessrole',
            name='organisation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='access_roles',
                to='organisations.organisation',
            ),
        ),
        migrations.AlterField(
            model_name='accessrole',
            name='code',
            field=models.CharField(max_length=120),
        ),
        migrations.AddConstraint(
            model_name='accessrole',
            constraint=models.UniqueConstraint(
                condition=models.Q(('organisation__isnull', False)),
                fields=('organisation', 'code'),
                name='unique_org_access_role_code',
            ),
        ),
        migrations.AddConstraint(
            model_name='accessrole',
            constraint=models.UniqueConstraint(
                condition=models.Q(('organisation__isnull', True)),
                fields=('code',),
                name='unique_global_access_role_code',
            ),
        ),
    ]
