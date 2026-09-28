from django.db import models
import uuid

class AdCampaign(models.Model):
    
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('google', 'Google'),
        ('tiktok', 'TikTok'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES
    )
    campaign_name = models.CharField(max_length=200)
    utm_source = models.CharField(max_length=100)
    utm_medium = models.CharField(max_length=100)
    utm_campaign = models.CharField(max_length=100)
    
    # Budget and spend in PKR
    budget = models.FloatField(default=0.0)
    spend = models.FloatField(default=0.0)
    
    # Performance from ad platform
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    
    # Revenue generated (from our events)
    revenue_generated = models.FloatField(default=0.0)
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ad_campaigns'
    
    @property
    def roas(self):
        if self.spend > 0:
            return round(self.revenue_generated / self.spend, 2)
        return 0
    
    @property
    def click_through_rate(self):
        if self.impressions > 0:
            return round(self.clicks / self.impressions * 100, 2)
        return 0
    
    def __str__(self):
        return f"{self.platform} - {self.campaign_name}"
