from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .models import AnalyticsMetric, SessionEvent


class EventCaptureViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_saves_client_event_timestamp_and_attribution(self):
        occurred_at = datetime.combine(
            date.today() - timedelta(days=1),
            time(12),
            tzinfo=timezone.utc,
        )

        response = self.client.post(
            '/api/events/capture/',
            data={
                'event_type': 'register',
                'session_id': 'session-1',
                'user_id': 'customer-1',
                'utm_source': 'newsletter',
                'occurred_at': occurred_at.isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        event = SessionEvent.objects.get()
        self.assertEqual(event.user_id, 'customer-1')
        self.assertEqual(event.utm_source, 'newsletter')
        self.assertEqual(event.occurred_at, occurred_at)


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


class FunnelViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_counts_purchase_and_checkout_complete_events(self):
        occurred_at = datetime.now(timezone.utc)
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='session-1',
            order_id='order-1',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='checkout_complete',
            session_id='session-2',
            order_id='order-2',
            occurred_at=occurred_at,
        )

        response = self.client.get('/api/dashboard/funnel/')

        self.assertEqual(response.status_code, 200)
        purchase_stage = next(
            stage for stage in response.data['funnel']
            if stage['stage'] == 'Purchase Completed'
        )
        self.assertEqual(purchase_stage['count'], 2)


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


class CalculateAllMetricsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_calculates_six_months_with_bounded_database_queries(self):
        target_date = date.today() - timedelta(days=1)
        occurred_at = datetime.combine(
            target_date,
            time(12),
            tzinfo=timezone.utc,
        )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='session-1',
            order_id='order-1',
            revenue=100,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='checkout_complete',
            session_id='session-2',
            order_id='order-2',
            revenue=50,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='page_view',
            session_id='session-1',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='register',
            session_id='session-3',
            user_id='customer-1',
            occurred_at=occurred_at,
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(
                '/api/dashboard/calculate-all/',
                data={},
                format='json',
                HTTP_ORIGIN='https://menze-plugin-frontend.vercel.app',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'success': True,
            'days_calculated': 180,
        })
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            '*',
        )
        self.assertLessEqual(len(queries), 10)

        metric = AnalyticsMetric.objects.get(metric_date=target_date)
        self.assertEqual(metric.total_sessions, 2)
        self.assertEqual(metric.orders_count, 2)
        self.assertEqual(metric.total_revenue, 150)
        self.assertEqual(metric.ltv, 75)
