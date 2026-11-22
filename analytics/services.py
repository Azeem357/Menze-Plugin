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
        
        total_sessions = events.values('session_id').distinct().count()
        page_views = events.filter(event_type='page_view').count()
        product_views = events.filter(event_type='product_view').count()
        add_to_cart = events.filter(event_type='add_to_cart').count()
        checkout_starts = events.filter(event_type='checkout_start').count()
        
        # Support both 'purchase' and 'checkout_complete'
        purchase_events = events.filter(
            event_type__in=['purchase', 'checkout_complete']
        )
        orders_count = purchase_events.count()
        
        # Read total from data field (synced orders) or revenue field
        total_revenue = sum(
    float(e.revenue) for e in purchase_events if e.revenue
)
        for e in purchase_events:
            if e.data and 'total' in e.data:
                try:
                    total_revenue += float(e.data['total'])
                except (ValueError, TypeError):
                    pass
            elif hasattr(e, 'revenue') and e.revenue:
                total_revenue += float(e.revenue)
        
        conversion_rate = (
            (orders_count / total_sessions * 100)
            if total_sessions > 0 else 0
        )
        
        campaigns = AdCampaign.objects.filter(is_active=True)
        total_spend = sum(c.spend for c in campaigns)
        roas = (total_revenue / total_spend if total_spend > 0 else 0)
        
        new_customers = events.filter(
            event_type='register'
        ).values('user_id').distinct().count()
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
        from datetime import timedelta
        results = []
        for days_ago in range(180, 0, -1):
            d = date.today() - timedelta(days=days_ago)
            result = self.calculate_daily_metrics(target_date=d)
            results.append(result)
        return results
    
    def calculate_ltv(self):
        purchase_events = SessionEvent.objects.filter(
            event_type__in=['purchase', 'checkout_complete']
        )

        if not purchase_events.exists():
            return 0

        user_orders = {}
        for event in purchase_events:
            uid = event.session_id
            if uid not in user_orders:
                user_orders[uid] = []
            revenue = float(event.revenue) if event.revenue else 0
            user_orders[uid].append(revenue)

        all_revenues = [r for orders in user_orders.values() for r in orders]
        if not all_revenues:
            return 0

        avg_order_value = sum(all_revenues) / len(all_revenues)
        avg_orders = sum(len(o) for o in user_orders.values()) / len(user_orders)

        return round(avg_order_value * avg_orders, 2)