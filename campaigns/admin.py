from django.contrib import admin
from .models import AdCampaign

@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'campaign_name', 'platform',
        'spend', 'revenue_generated',
        'roas', 'is_active'
    ]
    list_filter = ['platform', 'is_active']
