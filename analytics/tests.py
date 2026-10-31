from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient
from .models import AnalyticsMetric


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
