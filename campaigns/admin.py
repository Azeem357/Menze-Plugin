from django.contrib import admin
from .models import AdCampaign, CampaignDailyStat


class CampaignDailyStatInline(admin.TabularInline):
    model = CampaignDailyStat
    extra = 1

@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    inlines = [CampaignDailyStatInline]
    list_display = [
        'campaign_name', 'platform', 'roas',
        'click_through_rate', 'is_active'
    ]
    list_filter = ['platform', 'is_active']
