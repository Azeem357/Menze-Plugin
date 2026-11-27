from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from django.db.models import Count
from django.utils import timezone

from analytics.forecasting import build_revenue_forecast
from analytics.models import SessionEvent


class SalesPredictionView(APIView):
    def get(self, request):
        forecast = build_revenue_forecast(horizon_days=30)
        return Response({
            'model': forecast['model'],
            'predictions': forecast['daily_forecast'],
            'days': list(range(1, len(forecast['daily_forecast']) + 1)),
            'label': 'Next 30 Days Sales Baseline',
        })


class RecommendationView(APIView):
    def post(self, request):
        excluded = request.data.get('exclude_product_ids', [])
        if not isinstance(excluded, list) or not all(
            isinstance(product_id, (str, int)) for product_id in excluded
        ):
            return Response(
                {'error': 'exclude_product_ids must be a list of product IDs'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = timezone.localdate() - timedelta(days=30)
        popular = (
            SessionEvent.objects.filter(
                event_type__in=['product_view', 'add_to_cart', 'purchase'],
                occurred_at__date__gte=start_date,
                product_id__isnull=False,
            )
            .exclude(product_id='')
            .exclude(product_id__in=[str(value) for value in excluded])
            .values('product_id')
            .annotate(interactions=Count('session_id', distinct=True))
            .order_by('-interactions', 'product_id')[:10]
        )
        recommendations = [
            {
                'product_id': item['product_id'],
                'interactions': item['interactions'],
            }
            for item in popular
        ]
        return Response({
            'method': 'popular_products_from_recent_store_events',
            'recommendations': recommendations,
            'recommended_item': (
                recommendations[0]['product_id']
                if recommendations else None
            ),
            'message': (
                None if recommendations
                else 'No recent product activity is available to recommend.'
            ),
        })
