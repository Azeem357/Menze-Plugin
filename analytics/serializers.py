from rest_framework import serializers
from campaigns.models import AdCampaign
from .models import (
    AnalyticsMetric,
    CustomerAcquisition,
    SessionEvent,
)

class SessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionEvent
        fields = '__all__'

class SessionEventCreateSerializer(serializers.ModelSerializer):
    ad_campaign = serializers.PrimaryKeyRelatedField(
        queryset=AdCampaign.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SessionEvent
        fields = [
            'user_id', 'session_id', 'event_type',
            'page_url', 'product_id', 'utm_source',
            'utm_medium', 'utm_campaign', 'referrer',
            'device_type', 'time_on_page', 'revenue',
            'order_id', 'campaign_id', 'ad_campaign', 'occurred_at'
        ]

    def validate(self, attrs):
        event_type = attrs.get('event_type')
        order_id = attrs.get('order_id')
        if event_type in ('purchase', 'checkout_complete'):
            if not order_id:
                raise serializers.ValidationError({
                    'order_id': 'An order ID is required for purchase events.'
                })
            if attrs.get('revenue') is None:
                raise serializers.ValidationError({
                    'revenue': 'Revenue is required for purchase events.'
                })

        campaign = attrs.get('ad_campaign')
        utm_campaign = attrs.get('utm_campaign')
        utm_source = (attrs.get('utm_source') or '').strip().lower()
        platform_aliases = {
            'fb': 'facebook',
            'facebook': 'facebook',
            'ig': 'instagram',
            'instagram': 'instagram',
            'google': 'google',
            'tiktok': 'tiktok',
        }
        if campaign is None and utm_campaign:
            platform = platform_aliases.get(utm_source)
            if platform:
                matches = AdCampaign.objects.filter(
                    platform=platform,
                    utm_campaign__iexact=utm_campaign.strip(),
                )
                if matches.count() > 1:
                    raise serializers.ValidationError({
                        'utm_campaign': (
                            'This tracking campaign matches multiple '
                            'campaign records.'
                        )
                    })
                campaign = matches.first()
                if campaign is None:
                    raise serializers.ValidationError({
                        'utm_campaign': (
                            'Create a matching campaign record before '
                            'sending events for this ad.'
                        )
                    })
                attrs['ad_campaign'] = campaign

        if campaign is not None and utm_campaign:
            if (
                campaign.utm_campaign.casefold()
                != utm_campaign.strip().casefold()
            ):
                raise serializers.ValidationError({
                    'ad_campaign': (
                        'The campaign does not match utm_campaign.'
                    )
                })
        if campaign is not None and utm_source:
            expected_platform = platform_aliases.get(utm_source)
            if expected_platform and campaign.platform != expected_platform:
                raise serializers.ValidationError({
                    'ad_campaign': (
                        'The campaign platform does not match utm_source.'
                    )
                })

        if attrs.get('event_type') == 'register':
            customer_key = (
                f"user:{attrs['user_id']}"
                if attrs.get('user_id')
                else f"session:{attrs['session_id']}"
            )
            attrs['_customer_key'] = customer_key
        return attrs

    def create(self, validated_data):
        customer_key = validated_data.pop('_customer_key', None)
        event_type = validated_data.get('event_type')
        order_id = validated_data.get('order_id')
        if event_type in ('purchase', 'checkout_complete') and order_id:
            existing = SessionEvent.objects.filter(
                order_id=order_id,
                event_type__in=['purchase', 'checkout_complete'],
            ).first()
            if existing is not None:
                for field, value in validated_data.items():
                    if (
                        field == 'occurred_at'
                        and 'occurred_at' not in self.initial_data
                    ):
                        continue
                    setattr(existing, field, value)
                existing.save()
                return existing

        event = super().create(validated_data)
        if customer_key:
            acquisition, created = CustomerAcquisition.objects.get_or_create(
                customer_key=customer_key,
                defaults={
                    'campaign': event.ad_campaign,
                    'acquired_at': event.occurred_at,
                },
            )
            if not created and event.occurred_at < acquisition.acquired_at:
                acquisition.campaign = event.ad_campaign
                acquisition.acquired_at = event.occurred_at
                acquisition.save(update_fields=['campaign', 'acquired_at'])
        return event

class AnalyticsMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsMetric
        fields = '__all__'