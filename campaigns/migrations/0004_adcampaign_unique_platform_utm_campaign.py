from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0003_alter_adcampaign_clicks_alter_adcampaign_impressions_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='adcampaign',
            constraint=models.UniqueConstraint(
                Lower('utm_campaign'),
                'platform',
                name='unique_platform_utm_campaign',
            ),
        ),
    ]
