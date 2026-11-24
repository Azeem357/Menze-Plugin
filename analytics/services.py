from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from .models import AnalyticsMetric, SessionEvent
from campaigns.models import CampaignDailyStat


class MetricCalculator:
    
    def calculate_daily_metrics(self, target_date=None):
        if target_date is None:
            target_date = date.today()
        
        events = SessionEvent.objects.filter(
            occurred_at__date=target_date
        )
        
        visitor_events = events.exclude(
            event_type__in=['purchase', 'checkout_complete']
        )
        total_sessions = visitor_events.values(
            'session_id'
        ).distinct().count()
        page_views = events.filter(event_type='page_view').count()
        product_views = events.filter(event_type='product_view').count()
        add_to_cart = events.filter(event_type='add_to_cart').count()
        checkout_starts = events.filter(event_type='checkout_start').count()
        
        # Support both 'purchase' and 'checkout_complete'
        purchase_events = events.filter(
            event_type__in=['purchase', 'checkout_complete']
        )
        purchase_totals = purchase_events.aggregate(
            orders_count=Count('id'),
            total_revenue=Sum('revenue'),
        )
        orders_count = purchase_totals['orders_count']
        total_revenue = float(purchase_totals['total_revenue'] or 0)
        
        conversion_rate = (
            (orders_count / total_sessions * 100)
            if total_sessions > 0 else 0
        )
        
        total_spend = (
            CampaignDailyStat.objects.filter(
                stat_date=target_date
            ).aggregate(total=Sum('spend'))['total']
            or 0
        )
        total_spend = float(total_spend)
        roas = (total_revenue / total_spend if total_spend > 0 else 0)
        
        new_customers = events.filter(
            event_type='register'
        ).aggregate(
            total=Count(
                Coalesce('user_id', 'session_id'),
                distinct=True,
            )
        )['total']
        cac = (total_spend / new_customers if new_customers > 0 else 0)
        
        ltv = self.calculate_ltv()
        
        metric, created = AnalyticsMetric.objects.update_or_create(
            metric_date=target_date,
            defaults={
                'total_sessions': total_sessions,
                'page_views': page_views,
                'product_views': product_views,
                'add_to_cart_count': add_to_cart,
                'checkout_starts': checkout_starts,
                'orders_count': orders_count,
                'total_revenue': round(total_revenue, 2),
                'conversion_rate': round(conversion_rate, 2),
                'roas': round(roas, 2),
                'cac': round(cac, 2),
                'ltv': round(ltv, 2)
            }
        )
        
        return {
            'date': str(target_date),
            'sessions': total_sessions,
            'orders': orders_count,
            'revenue': total_revenue,
            'roas': roas,
            'cac': cac,
            'ltv': ltv,
            'created': created
        }
    
    def calculate_all_historical(self):
        """Calculate metrics for all past 6 months"""
        today = date.today()
        start_date = today - timedelta(days=180)
        end_date = today - timedelta(days=1)

        daily_stats = {
            entry['metric_date']: entry
            for entry in (
                SessionEvent.objects.filter(
                    occurred_at__date__gte=start_date,
                    occurred_at__date__lte=end_date,
                )
                .annotate(metric_date=TruncDate('occurred_at'))
                .values('metric_date')
                .annotate(
                    total_sessions=Count(
                        'session_id',
                        distinct=True,
                        filter=~Q(
                            event_type__in=[
                                'purchase',
                                'checkout_complete',
                            ]
                        ),
                    ),
                    page_views=Count(
                        'id', filter=Q(event_type='page_view')
                    ),
                    product_views=Count(
                        'id', filter=Q(event_type='product_view')
                    ),
                    add_to_cart=Count(
                        'id', filter=Q(event_type='add_to_cart')
                    ),
                    checkout_starts=Count(
                        'id', filter=Q(event_type='checkout_start')
                    ),
                    orders_count=Count(
                        'id',
                        filter=Q(
                            event_type__in=[
                                'purchase',
                                'checkout_complete',
                            ]
                        ),
                    ),
                    total_revenue=Sum(
                        'revenue',
                        filter=Q(
                            event_type__in=[
                                'purchase',
                                'checkout_complete',
                            ]
                        ),
                    ),
                    new_customers=Count(
                        Coalesce('user_id', 'session_id'),
                        filter=Q(event_type='register'),
                        distinct=True,
                    ),
                )
            )
        }
        daily_spend = dict(
            CampaignDailyStat.objects.filter(
                stat_date__gte=start_date,
                stat_date__lte=end_date,
            )
            .values('stat_date')
            .annotate(total_spend=Sum('spend'))
            .values_list('stat_date', 'total_spend')
        )
        ltv = self.calculate_ltv()
        existing_metrics = {
            metric.metric_date: metric
            for metric in AnalyticsMetric.objects.filter(
                metric_date__gte=start_date,
                metric_date__lte=end_date,
            )
        }

        results = []
        to_create = []
        to_update = []
        updated_at = timezone.now()
        metric_fields = [
            'total_sessions',
            'page_views',
            'product_views',
            'add_to_cart_count',
            'checkout_starts',
            'orders_count',
            'total_revenue',
            'conversion_rate',
            'roas',
            'cac',
            'ltv',
            'updated_at',
        ]

        for days_ago in range(180, 0, -1):
            target_date = today - timedelta(days=days_ago)
            stats = daily_stats.get(target_date, {})
            total_sessions = stats.get('total_sessions', 0)
            orders_count = stats.get('orders_count', 0)
            total_revenue = float(stats.get('total_revenue') or 0)
            new_customers = stats.get('new_customers', 0)
            total_spend = float(daily_spend.get(target_date) or 0)
            roas = total_revenue / total_spend if total_spend > 0 else 0
            cac = total_spend / new_customers if new_customers > 0 else 0
            defaults = {
                'total_sessions': total_sessions,
                'page_views': stats.get('page_views', 0),
                'product_views': stats.get('product_views', 0),
                'add_to_cart_count': stats.get('add_to_cart', 0),
                'checkout_starts': stats.get('checkout_starts', 0),
                'orders_count': orders_count,
                'total_revenue': round(total_revenue, 2),
                'conversion_rate': round(
                    orders_count / total_sessions * 100
                    if total_sessions > 0 else 0,
                    2,
                ),
                'roas': round(roas, 2),
                'cac': round(cac, 2),
                'ltv': round(ltv, 2),
                'updated_at': updated_at,
            }

            metric = existing_metrics.get(target_date)
            if metric is None:
                to_create.append(
                    AnalyticsMetric(metric_date=target_date, **defaults)
                )
                created = True
            else:
                for field, value in defaults.items():
                    setattr(metric, field, value)
                to_update.append(metric)
                created = False

            results.append({
                'date': str(target_date),
                'sessions': total_sessions,
                'orders': orders_count,
                'revenue': total_revenue,
                'roas': roas,
                'cac': cac,
                'ltv': ltv,
                'created': created,
            })

        AnalyticsMetric.objects.bulk_create(to_create, batch_size=50)
        AnalyticsMetric.objects.bulk_update(
            to_update,
            fields=metric_fields,
            batch_size=50,
        )
        return results
    
    def calculate_ltv(self):
        purchase_events = SessionEvent.objects.filter(
            event_type__in=['purchase', 'checkout_complete']
        )
        totals = purchase_events.aggregate(
            total_revenue=Sum('revenue'),
            customer_count=Count(
                Coalesce('user_id', 'session_id'),
                distinct=True,
            ),
        )
        customer_count = totals['customer_count']
        if not customer_count:
            return 0

        return round(
            float(totals['total_revenue'] or 0) / customer_count,
            2,
        )
