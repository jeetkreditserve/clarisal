from django.db import migrations, models
from django.db.models import Count


def deduplicate_ct_tax_slab_sets(apps, schema_editor):
    PayrollTaxSlabSet = apps.get_model('payroll', 'PayrollTaxSlabSet')
    db_alias = schema_editor.connection.alias

    duplicate_groups = (
        PayrollTaxSlabSet.objects.using(db_alias)
        .filter(organisation__isnull=True)
        .values('country_code', 'fiscal_year', 'is_old_regime', 'tax_category')
        .annotate(row_count=Count('id'))
        .filter(row_count__gt=1)
    )

    for group in duplicate_groups:
        candidates = list(
            PayrollTaxSlabSet.objects.using(db_alias)
            .filter(
                organisation__isnull=True,
                country_code=group['country_code'],
                fiscal_year=group['fiscal_year'],
                is_old_regime=group['is_old_regime'],
                tax_category=group['tax_category'],
            )
            .annotate(slab_count=Count('slabs'))
            .order_by('-slab_count', 'created_at', 'id')
        )
        if len(candidates) < 2:
            continue

        canonical = candidates[0]
        duplicates = candidates[1:]

        PayrollTaxSlabSet.objects.using(db_alias).filter(
            source_set_id__in=[duplicate.id for duplicate in duplicates]
        ).update(source_set=canonical)

        PayrollTaxSlabSet.objects.using(db_alias).filter(
            id__in=[duplicate.id for duplicate in duplicates]
        ).delete()


class Migration(migrations.Migration):
    atomic = False

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
        migrations.RunPython(deduplicate_ct_tax_slab_sets, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='payrolltaxslabset',
            constraint=models.UniqueConstraint(
                condition=models.Q(organisation__isnull=True),
                fields=('country_code', 'fiscal_year', 'is_old_regime', 'tax_category'),
                name='unique_ct_tax_slab_set_per_regime_category_year',
            ),
        ),
    ]
