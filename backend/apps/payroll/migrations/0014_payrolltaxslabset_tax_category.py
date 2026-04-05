from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0013_payrolltdschallan'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrolltaxslabset',
            name='tax_category',
            field=models.CharField(
                choices=[
                    ('INDIVIDUAL', 'Individual (age < 60)'),
                    ('SENIOR_CITIZEN', 'Senior Citizen (age 60\u201379)'),
                    ('SUPER_SENIOR_CITIZEN', 'Super Senior Citizen (age \u2265 80)'),
                ],
                default='INDIVIDUAL',
                help_text='Age-based taxpayer category. Determines different basic exemption thresholds in the old regime.',
                max_length=24,
            ),
        ),
        migrations.AlterModelOptions(
            name='payrolltaxslabset',
            options={'ordering': ['organisation_id', 'fiscal_year', 'is_old_regime', 'tax_category']},
        ),
        migrations.AddConstraint(
            model_name='payrolltaxslabset',
            constraint=models.UniqueConstraint(
                condition=models.Q(organisation__isnull=True),
                fields=('country_code', 'fiscal_year', 'is_old_regime', 'tax_category'),
                name='unique_ct_tax_slab_set_per_regime_category_year',
            ),
        ),
    ]
