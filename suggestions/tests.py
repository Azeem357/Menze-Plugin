from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.models import SessionEvent
from campaigns.models import AdCampaign, CampaignDailyStat
from .models import AISuggestion


class RuleSuggestionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_funnel_events(self):
        now = timezone.now()
        cart_sessions = [f'cart-{index}' for index in range(6)]
        for index in range(94):
            SessionEvent.objects.create(
                event_type='page_view',
                session_id=f'visitor-{index}',
                occurred_at=now,
            )
        for session_id in cart_sessions:
            SessionEvent.objects.create(
                event_type='page_view',
                session_id=session_id,
                occurred_at=now,
            )
            SessionEvent.objects.create(
                event_type='add_to_cart',
                session_id=session_id,
                occurred_at=now,
            )
        SessionEvent.objects.create(
            event_type='purchase',
            session_id=cart_sessions[0],
            order_id='order-1',
            revenue=50,
            occurred_at=now,
        )

    def test_generation_is_data_driven_idempotent_and_auto_resolves_stale_rules(self):
        self._create_funnel_events()

        first = self.client.post('/api/suggestions/generate/')
        second = self.client.post('/api/suggestions/generate/')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['created'], 2)
        self.assertEqual(second.data['created'], 0)
        self.assertEqual(
            AISuggestion.objects.filter(rule_key__isnull=False).count(),
            2,
        )

        cart_suggestion = AISuggestion.objects.get(
            rule_key='cart-abandonment',
        )
        done = self.client.post(
            f'/api/suggestions/{cart_suggestion.pk}/mark-done/',
        )
        self.assertEqual(done.status_code, 200)
        self.client.post('/api/suggestions/generate/')
        cart_suggestion.refresh_from_db()
        self.assertTrue(cart_suggestion.is_acted_on)

        SessionEvent.objects.all().delete()
        refreshed = self.client.post('/api/suggestions/generate/')
        self.assertEqual(refreshed.data['active'], 0)
        self.assertFalse(
            AISuggestion.objects.filter(
                rule_key='cart-abandonment',
                is_active=True,
            ).exists()
        )

    def test_campaign_spend_without_attributed_orders_creates_warning(self):
        campaign = AdCampaign.objects.create(
            platform='facebook',
            campaign_name='Summer sale',
            utm_source='facebook',
            utm_medium='paid_social',
            utm_campaign='summer-sale',
        )
        CampaignDailyStat.objects.create(
            campaign=campaign,
            stat_date=timezone.localdate() - timedelta(days=1),
            spend='500',
        )

        response = self.client.post('/api/suggestions/generate/')

        self.assertEqual(response.status_code, 200)
        suggestion = AISuggestion.objects.get(
            rule_key=f'campaign-no-orders-{campaign.pk}',
        )
        self.assertIn('Verify the campaign UTM link', suggestion.body)

    def test_low_activity_does_not_create_funnel_recommendations(self):
        SessionEvent.objects.create(
            event_type='page_view',
            session_id='one-visitor',
        )

        response = self.client.post('/api/suggestions/generate/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 0)
        self.assertFalse(
            AISuggestion.objects.filter(rule_key__isnull=False).exists()
        )

# Create your tests here.
