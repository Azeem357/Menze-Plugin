from rest_framework import serializers
from .models import AdCampaign

class AdCampaignSerializer(serializers.ModelSerializer):
    roas = serializers.ReadOnlyField()
    click_through_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = AdCampaign
        fields = '__all__'