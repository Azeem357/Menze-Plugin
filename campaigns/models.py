from django.db import models
from django.db.models import Sum
from django.db.models.functions import Lower
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
    spend = models.FloatField(
        default=0.0,
        help_text='Legacy aggregate; use daily stats for reporting.',
    )
    
    # Performance from ad platform
    impressions = models.IntegerField(
        default=0,
        help_text='Legacy aggregate; use daily stats for reporting.',
    )
    clicks = models.IntegerField(
        default=0,
        help_text='Legacy aggregate; use daily stats for reporting.',
    )
    
    # Revenue generated (from our events)
    revenue_generated = models.FloatField(
        default=0.0,
        help_text='Legacy manual value; attributed event revenue is used when daily stats exist.',
    )
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ad_campaigns'
        constraints = [
            models.UniqueConstraint(
                Lower('utm_campaign'),
                'platform',
                name='unique_platform_utm_campaign',
            ),
        ]
    
    @property
    def roas(self):
        daily_spend = self.daily_stats.aggregate(
            total=Sum('spend')
        )['total']
        if daily_spend is not None:
            attributed_revenue = self.campaign_events.filter(
                event_type__in=['purchase', 'checkout_complete']
            ).aggregate(total=Sum('revenue'))['total'] or 0
            if daily_spend > 0:
                return round(
                    float(attributed_revenue) / float(daily_spend), 2
                )
            return 0

        if self.spend > 0:
            return round(self.revenue_generated / self.spend, 2)
        return 0
    
    @property
    def click_through_rate(self):
        daily_stats = self.daily_stats.aggregate(
            impressions=Sum('impressions'),
            clicks=Sum('clicks'),
        )
        if daily_stats['impressions'] is not None:
            impressions = daily_stats['impressions']
            clicks = daily_stats['clicks'] or 0
            if impressions > 0:
                return round(clicks / impressions * 100, 2)
            return 0

        if self.impressions > 0:
            return round(self.clicks / self.impressions * 100, 2)
        return 0
    
    def __str__(self):
        return f"{self.platform} - {self.campaign_name}"


class CampaignDailyStat(models.Model):
    campaign = models.ForeignKey(
        AdCampaign,
        on_delete=models.CASCADE,
        related_name='daily_stats',
    )
    stat_date = models.DateField()
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'campaign_daily_stats'
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'stat_date'],
                name='unique_campaign_stat_date',
            ),
        ]
        ordering = ['-stat_date']

    def __str__(self):
        return f"{self.campaign} - {self.stat_date}"
