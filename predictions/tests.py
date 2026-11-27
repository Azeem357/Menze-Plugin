from datetime import datetime, time, timedelta, timezone

from django.test import TestCase
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from analytics.models import SessionEvent


class RealDataPredictionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_forecast_uses_recent_deduplicated_orders(self):
        yesterday = django_timezone.localdate() - timedelta(days=1)
        occurred_at = datetime.combine(
            yesterday,
            time(12),
            tzinfo=timezone.utc,
        )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='session-1',
            order_id='order-1',
            revenue=700,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='checkout_complete',
            session_id='session-1',
            order_id='order-1',
            revenue=700,
            occurred_at=occurred_at,
        )

        response = self.client.get('/api/predictions/?horizon=7')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['model']['status'], 'baseline')
        self.assertEqual(response.data['weekly']['value'], 700)
        self.assertEqual(response.data['monthly']['value'], 3000)
        self.assertIn('not a trained ML model', response.data['model']['message'])

        legacy_response = self.client.get('/api/predict/sales/')
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(len(legacy_response.data['predictions']), 30)
        self.assertEqual(set(legacy_response.data['predictions']), {100})

    def test_forecast_reports_offline_when_there_are_no_purchase_events(self):
        response = self.client.get('/api/predictions/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['model']['status'], 'offline')
        self.assertIsNone(response.data['weekly']['value'])
        self.assertEqual(response.data['history'], [])

    def test_forecast_rejects_unreasonable_horizon(self):
        response = self.client.get('/api/predictions/?horizon=366')

        self.assertEqual(response.status_code, 400)

    def test_recommendations_use_recent_tracked_product_activity(self):
        SessionEvent.objects.create(
            event_type='product_view',
            session_id='session-1',
            product_id='popular-product',
        )
        SessionEvent.objects.create(
            event_type='add_to_cart',
            session_id='session-1',
            product_id='popular-product',
        )
        SessionEvent.objects.create(
            event_type='product_view',
            session_id='session-2',
            product_id='popular-product',
        )
        SessionEvent.objects.create(
            event_type='product_view',
            session_id='session-3',
            product_id='other-product',
        )

        response = self.client.post(
            '/api/predict/recommend/',
            data={'exclude_product_ids': ['popular-product']},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['recommended_item'],
            'other-product',
        )
        self.assertEqual(
            response.data['method'],
            'popular_products_from_recent_store_events',
        )

    def test_recommendation_input_must_be_a_list_of_product_ids(self):
        response = self.client.post(
            '/api/predict/recommend/',
            data={'exclude_product_ids': 'not-a-list'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

# Create your tests here.
