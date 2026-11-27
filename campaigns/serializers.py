from rest_framework import serializers
from .models import AdCampaign

class AdCampaignSerializer(serializers.ModelSerializer):
    roas = serializers.ReadOnlyField()
    click_through_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = AdCampaign
        fields = '__all__'

    def validate(self, attrs):
        platform = attrs.get(
            'platform',
            self.instance.platform if self.instance else None,
        )
        utm_campaign = attrs.get(
            'utm_campaign',
            self.instance.utm_campaign if self.instance else None,
        )
        if platform and utm_campaign:
            utm_campaign = utm_campaign.strip()
            matches = AdCampaign.objects.filter(
                platform=platform,
                utm_campaign__iexact=utm_campaign,
            )
            if self.instance:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise serializers.ValidationError({
                    'utm_campaign': (
                        'A campaign with this platform and UTM campaign '
                        'already exists.'
                    )
                })
            attrs['utm_campaign'] = utm_campaign
        return attrs