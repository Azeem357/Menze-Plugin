from datetime import date, datetime, time, timedelta, timezone

from django.test import TestCase
from rest_framework.test import APIClient

from .models import AdCampaign, CampaignDailyStat


class CampaignPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.campaign = AdCampaign.objects.create(
            platform='facebook',
            campaign_name='Winter sale',
            utm_source='facebook',
            utm_medium='paid_social',
            utm_campaign='winter-sale',
        )

    def _capture(self, event_type, **data):
        payload = {
            'event_type': event_type,
            'session_id': 'session-1',
            'occurred_at': datetime.combine(
                date.today(),
                time(12),
                tzinfo=timezone.utc,
            ).isoformat(),
            'utm_source': 'facebook',
            'utm_medium': 'paid_social',
            'utm_campaign': 'winter-sale',
            **data,
        }
        return self.client.post(
            '/api/events/capture/',
            data=payload,
            format='json',
        )

    def test_campaign_metrics_use_attributed_orders_and_first_registration(self):
        today = date.today()
        CampaignDailyStat.objects.create(
            campaign=self.campaign,
            stat_date=today,
            spend='100.00',
            impressions=1000,
            clicks=50,
        )
        registration = self._capture(
            'register',
            user_id='customer-1',
        )
        self.assertEqual(registration.status_code, 201)

        old_purchase = self.client.post(
            '/api/events/capture/',
            data={
                'event_type': 'purchase',
                'session_id': 'session-old',
                'user_id': 'customer-1',
                'order_id': 'old-order',
                'revenue': 100,
                'occurred_at': datetime.combine(
                    today - timedelta(days=5),
                    time(12),
                    tzinfo=timezone.utc,
                ).isoformat(),
            },
            format='json',
        )
        self.assertEqual(old_purchase.status_code, 201)

        purchase_data = {
            'event_type': 'purchase',
            'session_id': 'session-1',
            'user_id': 'customer-1',
            'order_id': 'today-order',
            'revenue': 250,
        }
        first_purchase = self._capture(**purchase_data)
        duplicate_purchase = self._capture(**purchase_data)
        self.assertEqual(first_purchase.status_code, 201)
        self.assertEqual(duplicate_purchase.status_code, 201)

        response = self.client.get('/api/campaigns/performance/?days=1')

        self.assertEqual(response.status_code, 200)
        result = response.data['campaigns'][0]
        self.assertEqual(result['spend'], 100.0)
        self.assertEqual(result['revenue'], 250.0)
        self.assertEqual(result['orders'], 1)
        self.assertEqual(result['roas'], 2.5)
        self.assertEqual(result['new_customers'], 1)
        self.assertEqual(result['cac'], 100.0)
        self.assertEqual(result['ltv'], 350.0)
        self.assertEqual(result['click_through_rate'], 5.0)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.roas, 2.5)
        self.assertEqual(self.campaign.click_through_rate, 5.0)

    def test_unknown_paid_utm_campaign_is_rejected(self):
        response = self.client.post(
            '/api/events/capture/',
            data={
                'event_type': 'page_view',
                'session_id': 'session-unknown',
                'utm_source': 'facebook',
                'utm_campaign': 'not-configured',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('utm_campaign', response.data)

    def test_duplicate_platform_and_utm_campaign_is_rejected_case_insensitively(self):
        response = self.client.post(
            '/api/campaigns/',
            data={
                'platform': 'facebook',
                'campaign_name': 'Duplicate winter sale',
                'utm_source': 'facebook',
                'utm_medium': 'paid_social',
                'utm_campaign': 'WINTER-SALE',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('utm_campaign', response.data)

    def test_same_utm_campaign_is_allowed_for_different_platforms(self):
        response = self.client.post(
            '/api/campaigns/',
            data={
                'platform': 'instagram',
                'campaign_name': 'Winter sale on Instagram',
                'utm_source': 'instagram',
                'utm_medium': 'paid_social',
                'utm_campaign': 'winter-sale',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)

    def test_performance_rejects_invalid_date_range(self):
        response = self.client.get('/api/campaigns/performance/?days=0')

        self.assertEqual(response.status_code, 400)

# Create your tests here.
