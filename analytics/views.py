from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from datetime import date, timedelta
from .models import SessionEvent, AnalyticsMetric
from .serializers import (
    SessionEventSerializer,
    SessionEventCreateSerializer,
    AnalyticsMetricSerializer
)
from .services import MetricCalculator


# ══════════════════════════════════════════════
# SESSION EVENT VIEWS
# ══════════════════════════════════════════════

class CaptureEventView(generics.CreateAPIView):
    """
    POST /api/events/capture
    Receives events from tracker.js
    Generic CreateAPIView handles everything
    """
    queryset = SessionEvent.objects.all()
    serializer_class = SessionEventCreateSerializer


class EventListView(generics.ListAPIView):
    """
    GET /api/events/
    List all events — for admin debugging
    """
    queryset = SessionEvent.objects.all()
    serializer_class = SessionEventSerializer
    
    def get_queryset(self):
        """
        Optional filtering by event_type or date
        GET /api/events/?event_type=product_view
        GET /api/events/?days=7
        """
        queryset = SessionEvent.objects.all()
        
        # Filter by event type
        event_type = self.request.query_params.get(
            'event_type'
        )
        if event_type:
            queryset = queryset.filter(
                event_type=event_type
            )
        
        # Filter by days
        days = self.request.query_params.get('days')
        if days:
            start_date = date.today() - timedelta(
                days=int(days)
            )
            queryset = queryset.filter(
                occurred_at__date__gte=start_date
            )
        
        return queryset.order_by('-occurred_at')[:100]


class EventDetailView(generics.RetrieveAPIView):
    """
    GET /api/events/<id>/
    Get one specific event by ID
    """
    queryset = SessionEvent.objects.all()
    serializer_class = SessionEventSerializer


# ══════════════════════════════════════════════
# ANALYTICS METRIC VIEWS
# ══════════════════════════════════════════════

class MetricListView(generics.ListAPIView):
    """
    GET /api/metrics/
    List all daily metrics
    """
    queryset = AnalyticsMetric.objects.all()
    serializer_class = AnalyticsMetricSerializer
    
    def get_queryset(self):
        queryset = AnalyticsMetric.objects.all()
        
        days = self.request.query_params.get('days', 30)
        start_date = date.today() - timedelta(
            days=int(days)
        )
        
        return queryset.filter(
            metric_date__gte=start_date
        ).order_by('metric_date')


class MetricDetailView(generics.RetrieveAPIView):
    """
    GET /api/metrics/<id>/
    Get one specific metric record
    """
    queryset = AnalyticsMetric.objects.all()
    serializer_class = AnalyticsMetricSerializer


# ══════════════════════════════════════════════
# WEBHOOK VIEW
# (Custom logic — APIView is correct here)
# ══════════════════════════════════════════════

class OrderWebhookView(APIView):
    """
    POST /api/events/order-complete
    Called by store backend when order placed.
    Custom logic needed so we use APIView here.
    Generic views cannot handle this custom logic.
    """
    def post(self, request):
        data = request.data
        
        # Validate required fields
        if not data.get('order_id'):
            return Response(
                {'error': 'order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not data.get('total_amount'):
            return Response(
                {'error': 'total_amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the checkout_complete event
        event = SessionEvent.objects.create(
            user_id=data.get('user_id'),
            session_id=data.get(
                'session_id', 'webhook_session'
            ),
            event_type='checkout_complete',
            revenue=data.get('total_amount'),
            order_id=data.get('order_id'),
            utm_source=data.get('utm_source'),
            utm_medium=data.get('utm_medium'),
            utm_campaign=data.get('utm_campaign')
        )
        
        return Response({
            'success': True,
            'event_id': str(event.id),
            'message': 'Order event recorded'
        }, status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════
# DASHBOARD VIEWS
# (Complex custom logic — APIView is correct)
# ══════════════════════════════════════════════

class DashboardOverviewView(APIView):
    """
    GET /api/dashboard/overview?days=30
    Complex aggregation — APIView needed here.
    Generic views only work for simple CRUD.
    Custom aggregation needs APIView.
    """
    def get(self, request):
        days = int(
            request.query_params.get('days', 30)
        )
        start_date = date.today() - timedelta(days=days)
        
        metrics = AnalyticsMetric.objects.filter(
            metric_date__gte=start_date
        ).order_by('metric_date')
        
        if not metrics.exists():
            return Response({
                'message': 'No data yet',
                'summary': {},
                'chart': [],
                'traffic_sources': []
            })
        
        # Totals using Django aggregation
        totals = metrics.aggregate(
            total_revenue=Sum('total_revenue'),
            total_orders=Sum('orders_count'),
            total_sessions=Sum('total_sessions')
        )
        
        count = metrics.count()
        
        avg_conversion = (
            sum(m.conversion_rate for m in metrics)
            / count
        )
        avg_roas = sum(m.roas for m in metrics) / count
        avg_cac = sum(m.cac for m in metrics) / count
        avg_ltv = sum(m.ltv for m in metrics) / count
        
        # Chart data — daily breakdown
        chart_data = [
            {
                'date': m.metric_date.isoformat(),
                'revenue': m.total_revenue,
                'orders': m.orders_count,
                'sessions': m.total_sessions,
                'conversion_rate': m.conversion_rate
            }
            for m in metrics
        ]
        
        # Traffic sources
        traffic = self._get_traffic_sources(start_date)
        
        return Response({
            'summary': {
                'total_revenue': round(
                    totals['total_revenue'] or 0, 2
                ),
                'total_orders': (
                    totals['total_orders'] or 0
                ),
                'total_sessions': (
                    totals['total_sessions'] or 0
                ),
                'avg_conversion_rate': round(
                    avg_conversion, 2
                ),
                'avg_roas': round(avg_roas, 2),
                'avg_cac': round(avg_cac, 2),
                'avg_ltv': round(avg_ltv, 2)
            },
            'chart': chart_data,
            'traffic_sources': traffic
        })
    
    def _get_traffic_sources(self, start_date):
        events = SessionEvent.objects.filter(
            occurred_at__date__gte=start_date
        )
        
        sources = {}
        for event in events:
            source = event.utm_source or 'organic'
            if source not in sources:
                sources[source] = {
                    'sessions': 0,
                    'revenue': 0,
                    'orders': 0
                }
            sources[source]['sessions'] += 1
            if event.event_type == 'checkout_complete':
                sources[source]['revenue'] += (
                    event.revenue or 0
                )
                sources[source]['orders'] += 1
        
        return [
            {
                'source': k,
                'sessions': v['sessions'],
                'revenue': round(v['revenue'], 2),
                'orders': v['orders']
            }
            for k, v in sorted(
                sources.items(),
                key=lambda x: x[1]['sessions'],
                reverse=True
            )
        ]


class FunnelView(APIView):
    """
    GET /api/dashboard/funnel?days=30
    Custom calculation — APIView needed
    """
    def get(self, request):
        days = int(
            request.query_params.get('days', 30)
        )
        start_date = date.today() - timedelta(days=days)
        
        events = SessionEvent.objects.filter(
            occurred_at__date__gte=start_date
        )
        
        total_sessions = events.values(
            'session_id'
        ).distinct().count()
        
        if total_sessions == 0:
            return Response({
                'message': 'No sessions found',
                'funnel': []
            })
        
        def count_event(event_type):
            return events.filter(
                event_type=event_type
            ).count()
        
        def pct(val):
            return round(
                val / total_sessions * 100, 1
            )
        
        product_views   = count_event('product_view')
        add_to_cart     = count_event('add_to_cart')
        checkout_starts = count_event('checkout_start')
        purchases       = count_event('checkout_complete')
        
        return Response({
            'funnel': [
                {
                    'stage': 'Homepage Visits',
                    'count': total_sessions,
                    'percentage': 100,
                    'color': '#002060'
                },
                {
                    'stage': 'Product Views',
                    'count': product_views,
                    'percentage': pct(product_views),
                    'drop_off': 100 - pct(product_views),
                    'color': '#1F4E79'
                },
                {
                    'stage': 'Add to Cart',
                    'count': add_to_cart,
                    'percentage': pct(add_to_cart),
                    'drop_off': (
                        pct(product_views)
                        - pct(add_to_cart)
                    ),
                    'color': '#C9A84C'
                },
                {
                    'stage': 'Checkout Started',
                    'count': checkout_starts,
                    'percentage': pct(checkout_starts),
                    'drop_off': (
                        pct(add_to_cart)
                        - pct(checkout_starts)
                    ),
                    'color': '#7F6000'
                },
                {
                    'stage': 'Purchase Completed',
                    'count': purchases,
                    'percentage': pct(purchases),
                    'drop_off': (
                        pct(checkout_starts)
                        - pct(purchases)
                    ),
                    'color': '#375623'
                }
            ],
            'total_sessions': total_sessions,
            'overall_conversion': pct(purchases)
        })


class CalculateMetricsView(APIView):
    """
    POST /api/dashboard/calculate
    Trigger metric calculation manually
    Custom logic — APIView needed
    """
    def post(self, request):
        calculator = MetricCalculator()
        result = calculator.calculate_daily_metrics()
        
        return Response({
            'success': True,
            'result': result
        })


class ServeTrackerView(APIView):
    """
    GET /tracker.js
    Serves JavaScript tracking script
    """
    def get(self, request):
        import os
        from django.http import FileResponse
        
        tracker_path = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)
            ),
            'tracking-script',
            'tracker.js'
        )
        
        if not os.path.exists(tracker_path):
            return Response(
                {'error': 'tracker.js not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return FileResponse(
            open(tracker_path, 'rb'),
            content_type='application/javascript'
        )
