from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from campaigns.models import AdCampaign, CampaignDailyStat
from .models import AnalyticsMetric, SessionEvent
from .services import MetricCalculator


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


class OrderWebhookViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.campaign = AdCampaign.objects.create(
            platform='facebook',
            campaign_name='Winter sale',
            utm_source='facebook',
            utm_medium='paid_social',
            utm_campaign='winter-sale',
        )

    def test_order_webhook_sets_timestamp_campaign_and_is_idempotent(self):
        data = {
            'order_id': 'webhook-order',
            'total_amount': 75,
            'user_id': 'customer-1',
            'utm_source': 'facebook',
            'utm_medium': 'paid_social',
            'utm_campaign': 'winter-sale',
        }

        first = self.client.post(
            '/api/events/order-complete/',
            data=data,
            format='json',
        )
        self.assertEqual(first.status_code, 201)
        first_event = SessionEvent.objects.get()
        occurred_at = first_event.occurred_at
        self.assertIsNotNone(occurred_at)

        duplicate = self.client.post(
            '/api/events/order-complete/',
            data=data,
            format='json',
        )

        self.assertEqual(duplicate.status_code, 201)
        self.assertEqual(SessionEvent.objects.count(), 1)
        event = SessionEvent.objects.get()
        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(event.ad_campaign, self.campaign)


class PredictionsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_returns_baseline_forecast_from_recorded_orders(self):
        today = date.today()
        for days_ago in range(1, 8):
            occurred_at = datetime.combine(
                today - timedelta(days=days_ago),
                time(12),
                tzinfo=timezone.utc,
            )
            SessionEvent.objects.create(
                event_type='purchase',
                session_id=f'session-{days_ago}',
                order_id=f'order-{days_ago}',
                revenue=150,
                occurred_at=occurred_at,
            )

        response = self.client.get('/api/predictions/?horizon=7')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['weekly']['value'], 1050)
        self.assertEqual(response.data['monthly']['value'], 4500)
        self.assertEqual(len(response.data['history']), 23)
        self.assertIn('not a trained ML model', response.data['model']['message'])

    def test_returns_empty_state_when_metrics_do_not_exist(self):
        response = self.client.get('/api/predictions/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['model']['status'], 'offline')
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


class DashboardOverviewTrafficSourceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_sources_count_unique_sessions_and_unique_orders_without_metrics(self):
        occurred_at = datetime.combine(
            date.today(),
            time(12),
            tzinfo=timezone.utc,
        )
        SessionEvent.objects.create(
            event_type='page_view',
            session_id='facebook-session',
            utm_source='facebook',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='page_view',
            session_id='facebook-session',
            utm_source='facebook',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='facebook-session',
            order_id='order-1',
            revenue=125,
            utm_source='facebook',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='checkout_complete',
            session_id='facebook-session',
            order_id='order-1',
            revenue=125,
            utm_source='facebook',
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='page_view',
            session_id='organic-session',
            occurred_at=occurred_at,
        )

        response = self.client.get('/api/dashboard/overview/?days=1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['total_sessions'], 2)
        self.assertEqual(
            response.data['traffic_sources'],
            [
                {
                    'source': 'facebook',
                    'sessions': 1,
                    'revenue': 125,
                    'orders': 1,
                },
                {
                    'source': 'organic',
                    'sessions': 1,
                    'revenue': 0,
                    'orders': 0,
                },
            ],
        )

    def test_rejects_invalid_days_range(self):
        response = self.client.get('/api/dashboard/overview/?days=0')

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
                'items': [{
                    'product_id': 10,
                    'product_name': 'Bestseller',
                    'quantity': 2,
                    'price': '12.50',
                }],
            },
            {
                'order_id': 2,
                'total': '25.00',
                'created_at': '2026-11-22T13:57:53.013006+00:00',
                'items': [{
                    'product_id': 10,
                    'product_name': 'Bestseller',
                    'quantity': 2,
                    'price': '12.50',
                }],
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
        self.assertEqual(
            SessionEvent.objects.get(order_id='2').order_items,
            [{
                'product_id': '10',
                'product_name': 'Bestseller',
                'quantity': 2,
                'price': '12.50',
            }],
        )

    @patch('requests.get')
    def test_sync_backfills_items_on_existing_orders(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = [{
            'order_id': 1,
            'total': '15.00',
            'created_at': '2026-11-22T13:57:26.321171+00:00',
            'items': [{
                'product_id': 4,
                'product_name': 'Existing order product',
                'quantity': 3,
                'price': '5.00',
            }],
        }]
        event = SessionEvent.objects.create(
            event_type='purchase',
            session_id='order-1',
            order_id='1',
            revenue=15.00,
        )

        response = self.client.post('/api/sync/orders/', data={}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'synced': 0, 'total': 1})
        event.refresh_from_db()
        self.assertEqual(event.order_items[0]['product_id'], '4')
        self.assertEqual(event.order_items[0]['price'], '5.00')


class ProductSalesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_ranks_sales_by_units_and_deduplicates_order_events(self):
        today = django_timezone.localdate()
        occurred_at = datetime.combine(
            today,
            time(12),
            tzinfo=timezone.utc,
        )
        items = [{
            'product_id': 'shirt-1',
            'product_name': 'Menze shirt',
            'quantity': 2,
            'price': 25.0,
        }]
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='order-1',
            order_id='order-1',
            order_items=items,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='checkout_complete',
            session_id='order-1',
            order_id='order-1',
            order_items=items,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='order-2',
            order_id='order-2',
            order_items=[{
                'product_id': 'hat-1',
                'product_name': 'Menze hat',
                'quantity': 1,
                'price': 40.0,
            }],
            occurred_at=occurred_at,
        )

        response = self.client.get(
            '/api/analytics/product-sales/?period=today'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['orders_with_items'], 2)
        self.assertEqual(response.data['products'][0], {
            'product_id': 'shirt-1',
            'product_name': 'Menze shirt',
            'units_sold': 2,
            'revenue': 50.0,
            'orders': 1,
        })

    def test_reports_legacy_orders_without_line_items(self):
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='legacy-order',
            order_id='legacy-order',
            occurred_at=django_timezone.now(),
        )

        response = self.client.get('/api/analytics/product-sales/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['orders_without_items'], 1)
        self.assertEqual(response.data['products'], [])

    def test_rejects_unsupported_period(self):
        response = self.client.get(
            '/api/analytics/product-sales/?period=month'
        )

        self.assertEqual(response.status_code, 400)


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


class DailyMetricCampaignSpendTests(TestCase):
    def test_daily_roas_and_cac_use_spend_for_that_date(self):
        target_date = date.today() - timedelta(days=1)
        occurred_at = datetime.combine(
            target_date,
            time(12),
            tzinfo=timezone.utc,
        )
        campaign = AdCampaign.objects.create(
            platform='facebook',
            campaign_name='Winter sale',
            utm_source='facebook',
            utm_medium='paid_social',
            utm_campaign='winter-sale',
        )
        CampaignDailyStat.objects.create(
            campaign=campaign,
            stat_date=target_date,
            spend='100.00',
        )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id='session-1',
            user_id='customer-1',
            order_id='order-1',
            revenue=250,
            occurred_at=occurred_at,
        )
        SessionEvent.objects.create(
            event_type='register',
            session_id='session-1',
            user_id='customer-1',
            occurred_at=occurred_at,
        )

        result = MetricCalculator().calculate_daily_metrics(target_date)

        self.assertEqual(result['roas'], 2.5)
        self.assertEqual(result['cac'], 100.0)
