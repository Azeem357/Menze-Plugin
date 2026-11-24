from datetime import date, timedelta

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from analytics.models import CustomerAcquisition, SessionEvent
from .models import AdCampaign, CampaignDailyStat
from .serializers import AdCampaignSerializer


PURCHASE_EVENT_TYPES = ['purchase', 'checkout_complete']


def _sum_unique_orders(events):
    seen_orders = set()
    revenue = 0.0
    order_count = 0
    for event in events.only('id', 'order_id', 'revenue'):
        key = event.order_id or str(event.pk)
        if key in seen_orders:
            continue
        seen_orders.add(key)
        order_count += 1
        revenue += float(event.revenue or 0)
    return revenue, order_count


class CampaignListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/campaigns/     → list all campaigns
    POST /api/campaigns/     → create new campaign
    One view handles both
    """
    queryset = AdCampaign.objects.all()
    serializer_class = AdCampaignSerializer
    
    def get_queryset(self):
        queryset = AdCampaign.objects.all()
        
        # Filter by platform
        platform = self.request.query_params.get(
            'platform'
        )
        if platform:
            queryset = queryset.filter(
                platform=platform
            )
        
        # Filter active only
        active = self.request.query_params.get('active')
        if active == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-created_at')


class CampaignDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    GET    /api/campaigns/<id>/ → get one campaign
    PUT    /api/campaigns/<id>/ → update campaign
    DELETE /api/campaigns/<id>/ → delete campaign
    One view handles all three
    """
    queryset = AdCampaign.objects.all()
    serializer_class = AdCampaignSerializer


class CampaignUpdateSpendView(APIView):
    """
    POST /api/campaigns/<id>/update-spend/
    Records current-day campaign delivery totals.
    """
    def post(self, request, pk):
        try:
            campaign = AdCampaign.objects.get(pk=pk)
        except AdCampaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        campaign.spend = request.data.get(
            'spend', campaign.spend
        )
        campaign.impressions = request.data.get(
            'impressions', campaign.impressions
        )
        campaign.clicks = request.data.get(
            'clicks', campaign.clicks
        )
        campaign.save()
        CampaignDailyStat.objects.update_or_create(
            campaign=campaign,
            stat_date=timezone.localdate(),
            defaults={
                'spend': campaign.spend,
                'impressions': campaign.impressions,
                'clicks': campaign.clicks,
            },
        )
        
        return Response({
            'success': True,
            'campaign': AdCampaignSerializer(
                campaign
            ).data
        })


class CampaignPerformanceView(APIView):
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            return Response(
                {'error': 'days must be an integer from 1 to 3650'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if days < 1 or days > 3650:
            return Response(
                {'error': 'days must be an integer from 1 to 3650'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        results = []
        for campaign in AdCampaign.objects.all().order_by('campaign_name'):
            stats = campaign.daily_stats.filter(
                stat_date__range=(start_date, end_date)
            ).aggregate(
                spend=Sum('spend'),
                impressions=Sum('impressions'),
                clicks=Sum('clicks'),
            )
            spend = float(stats['spend'] or 0)
            attributed_events = SessionEvent.objects.filter(
                ad_campaign=campaign,
                event_type__in=PURCHASE_EVENT_TYPES,
                occurred_at__date__range=(start_date, end_date),
            ).order_by('occurred_at')
            revenue, orders = _sum_unique_orders(attributed_events)

            acquisitions = CustomerAcquisition.objects.filter(
                campaign=campaign
            )
            acquired_in_period = acquisitions.filter(
                acquired_at__date__range=(start_date, end_date)
            ).count()
            customer_keys = list(
                acquisitions.values_list('customer_key', flat=True)
            )
            user_ids = [
                key[len('user:'):]
                for key in customer_keys
                if key.startswith('user:')
            ]
            session_ids = [
                key[len('session:'):]
                for key in customer_keys
                if key.startswith('session:')
            ]
            customer_filter = Q(user_id__in=user_ids) | Q(
                session_id__in=session_ids
            )
            lifetime_events = SessionEvent.objects.filter(
                customer_filter,
                event_type__in=PURCHASE_EVENT_TYPES,
            ).order_by('occurred_at')
            lifetime_revenue, _ = _sum_unique_orders(lifetime_events)
            customer_count = len(customer_keys)

            results.append({
                'campaign_id': str(campaign.pk),
                'campaign_name': campaign.campaign_name,
                'platform': campaign.platform,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'spend': round(spend, 2),
                'impressions': stats['impressions'] or 0,
                'clicks': stats['clicks'] or 0,
                'click_through_rate': (
                    round(stats['clicks'] / stats['impressions'] * 100, 2)
                    if stats['impressions'] else 0
                ),
                'revenue': round(revenue, 2),
                'orders': orders,
                'roas': round(revenue / spend, 2) if spend else 0,
                'new_customers': acquired_in_period,
                'cac': (
                    round(spend / acquired_in_period, 2)
                    if acquired_in_period else 0
                ),
                'ltv': (
                    round(lifetime_revenue / customer_count, 2)
                    if customer_count else 0
                ),
            })

        return Response({
            'days': days,
            'campaigns': results,
        })
