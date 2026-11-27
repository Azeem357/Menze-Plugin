from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_sessionevent_ad_campaign_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionevent',
            name='order_items',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
