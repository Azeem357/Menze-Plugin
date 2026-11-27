from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from analytics.models import SessionEvent
from campaigns.models import AdCampaign
from .models import AISuggestion


PURCHASE_EVENT_TYPES = ('purchase', 'checkout_complete')


def _build_candidates():
    today = timezone.localdate()
    start_date = today - timedelta(days=29)
    recent_events = list(
        SessionEvent.objects.filter(
            occurred_at__date__range=(start_date, today),
            event_type__in=[
                'page_view',
                'add_to_cart',
                *PURCHASE_EVENT_TYPES,
            ],
        ).values('session_id', 'event_type')
    )
    page_sessions = {
        event['session_id']
        for event in recent_events
        if event['event_type'] == 'page_view'
    }
    cart_sessions = {
        event['session_id']
        for event in recent_events
        if event['event_type'] == 'add_to_cart'
    }
    purchasing_sessions = {
        event['session_id']
        for event in recent_events
        if event['event_type'] in PURCHASE_EVENT_TYPES
    }
    candidates = []

    if len(page_sessions) >= 20:
        conversion = len(page_sessions & purchasing_sessions) / len(page_sessions)
        if conversion < 0.02:
            candidates.append({
                'rule_key': 'low-store-conversion',
                'suggestion_type': 'internal',
                'title': 'Review the store conversion funnel',
                'body': (
                    f'{len(page_sessions)} tracked visitor sessions and '
                    f'{len(page_sessions & purchasing_sessions)} purchasing '
                    'sessions were recorded in the last 30 days. Review product '
                    'pages, shipping costs, and checkout steps before increasing '
                    'advertising spend.'
                ),
                'source': 'analytics:low-store-conversion',
                'priority': 'high' if conversion < 0.01 else 'medium',
            })

    if len(cart_sessions) >= 5:
        cart_conversion = (
            len(cart_sessions & purchasing_sessions) / len(cart_sessions)
        )
        if cart_conversion < 0.3:
            candidates.append({
                'rule_key': 'cart-abandonment',
                'suggestion_type': 'internal',
                'title': 'Investigate cart abandonment',
                'body': (
                    f'{len(cart_sessions)} sessions added an item to the cart, '
                    f'but only {len(cart_sessions & purchasing_sessions)} of '
                    'those sessions recorded a purchase in the last 30 days. '
                    'Check checkout errors, payment options, and unexpected fees.'
                ),
                'source': 'analytics:cart-abandonment',
                'priority': 'high' if cart_conversion < 0.1 else 'medium',
            })

    campaign_start = today - timedelta(days=6)
    for campaign in AdCampaign.objects.filter(is_active=True).order_by('pk'):
        spend = campaign.daily_stats.filter(
            stat_date__range=(campaign_start, today),
        ).aggregate(total=Sum('spend'))['total'] or 0
        if spend <= 0:
            continue
        has_orders = campaign.campaign_events.filter(
            event_type__in=PURCHASE_EVENT_TYPES,
            occurred_at__date__range=(campaign_start, today),
        ).exists()
        if not has_orders:
            candidates.append({
                'rule_key': f'campaign-no-orders-{campaign.pk}',
                'suggestion_type': 'external',
                'title': (
                    'Review campaign delivery: '
                    f'{campaign.campaign_name[:160]}'
                ),
                'body': (
                    f'{campaign.platform.title()} reported spend of '
                    f'PKR {float(spend):,.2f} in the last 7 days, but Menze '
                    'has no attributed purchase events for this campaign. '
                    'Verify the campaign UTM link and purchase tracking before '
                    'changing its budget.'
                ),
                'source': f'analytics:campaign:{campaign.pk}',
                'priority': 'medium',
            })

    return candidates


@transaction.atomic
def refresh_rule_suggestions():
    candidates = _build_candidates()
    active_keys = {candidate['rule_key'] for candidate in candidates}
    existing = {
        suggestion.rule_key: suggestion
        for suggestion in AISuggestion.objects.select_for_update().filter(
            rule_key__isnull=False,
        )
    }
    created = 0

    for candidate in candidates:
        suggestion = existing.get(candidate['rule_key'])
        if suggestion is None:
            suggestion, was_created = AISuggestion.objects.get_or_create(
                rule_key=candidate['rule_key'],
                defaults={
                    **candidate,
                    'is_active': True,
                },
            )
            if was_created:
                existing[candidate['rule_key']] = suggestion
                created += 1
                continue

        was_inactive = not suggestion.is_active
        for field in (
            'suggestion_type',
            'title',
            'body',
            'source',
            'priority',
        ):
            setattr(suggestion, field, candidate[field])
        suggestion.is_active = True
        if was_inactive:
            suggestion.is_acted_on = False
            suggestion.acted_on_at = None
        suggestion.save()

    stale = AISuggestion.objects.filter(
        rule_key__isnull=False,
        is_active=True,
    )
    if active_keys:
        stale = stale.exclude(rule_key__in=active_keys)
    stale.update(is_active=False)

    return {
        'created': created,
        'active': AISuggestion.objects.filter(
            is_active=True,
            is_acted_on=False,
        ).count(),
    }
