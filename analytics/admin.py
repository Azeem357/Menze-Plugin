from django.contrib import admin
from .models import SessionEvent, AnalyticsMetric

@admin.register(SessionEvent)
class SessionEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'session_id',
        'user_id', 'utm_source',
        'revenue', 'occurred_at'
    ]
    list_filter = ['event_type', 'utm_source', 'device_type']
    search_fields = ['session_id', 'user_id', 'product_id']
    readonly_fields = ['id', 'occurred_at']

@admin.register(AnalyticsMetric)
class AnalyticsMetricAdmin(admin.ModelAdmin):
    list_display = [
        'metric_date', 'total_sessions',
        'orders_count', 'total_revenue',
        'conversion_rate', 'roas', 'cac', 'ltv'
    ]
    readonly_fields = ['id', 'created_at']
