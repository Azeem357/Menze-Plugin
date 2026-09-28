from .models import SessionEvent, AnalyticsMetric
from campaigns.models import AdCampaign
from datetime import date

class MetricCalculator:
    
    def calculate_daily_metrics(self, target_date=None):
        if target_date is None:
            target_date = date.today()
        
        events = SessionEvent.objects.filter(
            occurred_at__date=target_date
        )
        
        if not events.exists():
            return {'message': 'No events for this date'}
        
        # Count by type
        total_sessions = events.values(
            'session_id'
        ).distinct().count()
        
        page_views = events.filter(
            event_type='page_view'
        ).count()
        
        product_views = events.filter(
            event_type='product_view'
        ).count()
        
        add_to_cart = events.filter(
            event_type='add_to_cart'
        ).count()
        
        checkout_starts = events.filter(
            event_type='checkout_start'
        ).count()
        
        purchase_events = events.filter(
            event_type='checkout_complete'
        )
        orders_count = purchase_events.count()
        
        total_revenue = sum(
            e.revenue or 0 for e in purchase_events
        )
        
        # Conversion rate
        conversion_rate = (
            (orders_count / total_sessions * 100)
            if total_sessions > 0 else 0
        )
        
        # ROAS
        campaigns = AdCampaign.objects.filter(
            is_active=True
        )
        total_spend = sum(c.spend for c in campaigns)
        roas = (
            total_revenue / total_spend
            if total_spend > 0 else 0
        )
        
        # CAC
        new_customers = events.filter(
            event_type='register',
            utm_source__isnull=False
        ).values('user_id').distinct().count()
        
        cac = (
            total_spend / new_customers
            if new_customers > 0 else 0
        )
        
        # LTV
        ltv = self.calculate_ltv()
        
        # Save or update metric
        metric, created = AnalyticsMetric.objects\
            .update_or_create(
                metric_date=target_date,
                defaults={
                    'total_sessions': total_sessions,
                    'page_views': page_views,
                    'product_views': product_views,
                    'add_to_cart_count': add_to_cart,
                    'checkout_starts': checkout_starts,
                    'orders_count': orders_count,
                    'total_revenue': round(total_revenue, 2),
                    'conversion_rate': round(
                        conversion_rate, 2
                    ),
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
            'conversion_rate': conversion_rate,
            'roas': roas,
            'cac': cac,
            'ltv': ltv,
            'created': created
        }
    
    def calculate_ltv(self):
        purchase_events = SessionEvent.objects.filter(
            event_type='checkout_complete',
            user_id__isnull=False
        )
        
        if not purchase_events.exists():
            return 0
        
        user_orders = {}
        for event in purchase_events:
            uid = event.user_id
            if uid not in user_orders:
                user_orders[uid] = []
            user_orders[uid].append(event.revenue or 0)
        
        qualifying = {
            uid: orders
            for uid, orders in user_orders.items()
            if len(orders) >= 2
        }
        
        if not qualifying:
            return 0
        
        all_revenues = [
            r for orders in qualifying.values()
            for r in orders
        ]
        avg_order_value = (
            sum(all_revenues) / len(all_revenues)
        )
        avg_orders = (
            sum(len(o) for o in qualifying.values())
            / len(qualifying)
        )
        
        return round(avg_order_value * avg_orders, 2)