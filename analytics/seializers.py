from rest_framework import serializers
from .models import SessionEvent, AnalyticsMetric

class SessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionEvent
        fields = '__all__'

class SessionEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionEvent
        fields = [
            'user_id', 'session_id', 'event_type',
            'page_url', 'product_id', 'utm_source',
            'utm_medium', 'utm_campaign', 'referrer',
            'device_type', 'time_on_page', 'revenue',
            'order_id', 'campaign_id'
        ]

class AnalyticsMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsMetric
        fields = '__all__'