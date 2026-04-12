from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('performance', '0002_appraisalcycle_activated_at_and_more'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='calibrationsessionentry',
            new_name='performance_session_b09e85_idx',
            old_name='performance_session_54d2b3_idx',
        ),
        migrations.RenameIndex(
            model_name='feedbackresponse',
            new_name='performance_submitt_b6e474_idx',
            old_name='performance_submitte_338f0d_idx',
        ),
    ]
