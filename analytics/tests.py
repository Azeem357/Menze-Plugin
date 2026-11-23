from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from .models import AnalyticsMetric, SessionEvent


class PredictionsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_returns_baseline_forecast_from_metrics(self):
        today = date.today()
        AnalyticsMetric.objects.create(
            metric_date=today - timedelta(days=1),
            total_revenue=100
        )
        AnalyticsMetric.objects.create(
            metric_date=today,
            total_revenue=200
        )

        response = self.client.get('/api/predictions/?horizon=7')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['weekly']['value'], 1050)
        self.assertEqual(response.data['monthly']['value'], 4500)
        self.assertEqual(len(response.data['history']), 1)
        self.assertEqual(response.data['history'][0]['variance'], 100)
        self.assertIn('no trained ML model', response.data['model']['message'])

    def test_returns_empty_state_when_metrics_do_not_exist(self):
        response = self.client.get('/api/predictions/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['weekly']['value'])
        self.assertEqual(response.data['history'], [])

    def test_rejects_invalid_horizon(self):
        response = self.client.get('/api/predictions/?horizon=0')

        self.assertEqual(response.status_code, 400)


class SyncOrdersViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('requests.get')
    def test_syncs_new_orders_without_duplicates_and_returns_cors_header(
        self, get
    ):
        orders = [
            {
                'order_id': 1,
                'total': '15.00',
                'created_at': '2026-11-22T13:57:26.321171+00:00',
            },
            {
                'order_id': 2,
                'total': '25.00',
                'created_at': '2026-11-22T13:57:53.013006+00:00',
            },
            {
                'order_id': 2,
                'total': '25.00',
                'created_at': '2026-11-22T13:57:53.013006+00:00',
            },
        ]
        get.return_value.status_code = 200
        get.return_value.json.return_value = orders
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='order-1',
            order_id='1',
            revenue=15.00,
        )

        response = self.client.post(
            '/api/sync/orders/',
            data={},
            format='json',
            HTTP_ORIGIN='https://menze-plugin-frontend.vercel.app',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'synced': 1, 'total': 3})
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            '*',
        )
        self.assertEqual(
            SessionEvent.objects.filter(event_type='purchase').count(),
            2,
        )
