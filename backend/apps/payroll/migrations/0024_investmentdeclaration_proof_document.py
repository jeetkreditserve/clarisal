from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
        ('payroll', '0023_payrollrunitem_epf_eps_split'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentdeclaration',
            name='proof_document',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='investment_declaration_proofs',
                to='documents.document',
            ),
        ),
    ]
