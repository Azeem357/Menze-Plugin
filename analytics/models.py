from django.db import models
import uuid

class SessionEvent(models.Model):
    
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('product_view', 'Product View'),
        ('add_to_cart', 'Add to Cart'),
        ('checkout_start', 'Checkout Start'),
        ('checkout_complete', 'Checkout Complete'),
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
    
    # Revenue (only for checkout_complete)
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
    
    # When
    occurred_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'session_events'
        ordering = ['-occurred_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.session_id}"


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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_metrics'
        ordering = ['-metric_date']
    
    def __str__(self):
        return f"Metrics for {self.metric_date}"
