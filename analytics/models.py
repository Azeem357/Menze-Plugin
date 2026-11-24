from django.db import models
from django.utils import timezone
import uuid

class SessionEvent(models.Model):
    
    EVENT_TYPES = [
    ('page_view', 'Page View'),
    ('product_view', 'Product View'),
    ('add_to_cart', 'Add to Cart'),
    ('checkout_start', 'Checkout Start'),
    ('checkout_complete', 'Checkout Complete'),
    ('checkout', 'Checkout'),
    ('purchase', 'Purchase'),
    ('login', 'Login'),
    ('register', 'Register'),
    ('wishlist_add', 'Wishlist Add'),
]
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Who did it
    user_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=100)
    
    # What they did
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES
    )
    
    # Where they were
    page_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    product_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    
    # Traffic source
    utm_source = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    utm_medium = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    utm_campaign = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    referrer = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    
    # Device
    device_type = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )
    
    # Engagement
    time_on_page = models.IntegerField(
        null=True,
        blank=True
    )
    
    # Revenue for completed purchase events
    revenue = models.FloatField(
        null=True,
        blank=True
    )
    order_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    campaign_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    ad_campaign = models.ForeignKey(
        'campaigns.AdCampaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='campaign_events',
        db_column='ad_campaign_id',
    )
    
    # When
    occurred_at = models.DateTimeField(
        default=timezone.now,
        null=True,
        blank=True,
    )
    
    class Meta:
        db_table = 'session_events'
        ordering = ['-occurred_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.session_id}"


class CustomerAcquisition(models.Model):
    customer_key = models.CharField(max_length=205, unique=True)
    campaign = models.ForeignKey(
        'campaigns.AdCampaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='customer_acquisitions',
    )
    acquired_at = models.DateTimeField()

    class Meta:
        db_table = 'customer_acquisitions'
        ordering = ['acquired_at']

    def __str__(self):
        return self.customer_key


class AnalyticsMetric(models.Model):
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    metric_date = models.DateField(unique=True)
    
    # Traffic
    total_sessions = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    
    # Funnel
    product_views = models.IntegerField(default=0)
    add_to_cart_count = models.IntegerField(default=0)
    checkout_starts = models.IntegerField(default=0)
    orders_count = models.IntegerField(default=0)
    
    # Revenue
    total_revenue = models.FloatField(default=0.0)
    
    # Calculated KPIs
    conversion_rate = models.FloatField(default=0.0)
    roas = models.FloatField(default=0.0)
    cac = models.FloatField(default=0.0)
    ltv = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=False, default=None, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_metrics'
        ordering = ['-metric_date']
    
    def __str__(self):
        return f"Metrics for {self.metric_date}"
