from datetime import timedelta

from django.utils import timezone

from .models import SessionEvent


PURCHASE_EVENT_TYPES = ('purchase', 'checkout_complete')
FORECAST_HISTORY_DAYS = 30
FORECAST_WINDOW_DAYS = 7


def build_revenue_forecast(horizon_days=7):
    end_date = timezone.localdate() - timedelta(days=1)
    start_date = end_date - timedelta(days=FORECAST_HISTORY_DAYS - 1)
    events = (
        SessionEvent.objects.filter(
            event_type__in=PURCHASE_EVENT_TYPES,
            occurred_at__date__range=(start_date, end_date),
        )
        .order_by('occurred_at', 'id')
        .values('id', 'order_id', 'revenue', 'occurred_at')
        .iterator(chunk_size=1000)
    )

    daily_revenue = {}
    seen_orders = set()
    has_sales = False
    for event in events:
        has_sales = True
        order_key = event['order_id'] or str(event['id'])
        if order_key in seen_orders:
            continue
        seen_orders.add(order_key)
        event_date = timezone.localtime(event['occurred_at']).date()
        daily_revenue[event_date] = (
            daily_revenue.get(event_date, 0.0)
            + float(event['revenue'] or 0)
        )

    dates = [
        start_date + timedelta(days=offset)
        for offset in range(FORECAST_HISTORY_DAYS)
    ]
    actuals = [round(daily_revenue.get(day, 0.0), 2) for day in dates]
    recent_actuals = actuals[-FORECAST_WINDOW_DAYS:]
    daily_average = (
        sum(recent_actuals) / len(recent_actuals)
        if has_sales and recent_actuals
        else None
    )

    history = []
    for index in range(FORECAST_WINDOW_DAYS, len(dates)):
        predicted = sum(
            actuals[index - FORECAST_WINDOW_DAYS:index]
        ) / FORECAST_WINDOW_DAYS
        actual = actuals[index]
        history.append({
            'period': dates[index].isoformat(),
            'predicted': round(predicted, 2),
            'actual': actual,
            'variance': (
                round((actual - predicted) / predicted * 100, 2)
                if predicted else None
            ),
        })

    if daily_average is None:
        return {
            'model': {
                'status': 'offline',
                'title': 'Forecast unavailable',
                'message': (
                    'No completed purchase events were recorded in the '
                    'last 30 days.'
                ),
            },
            'daily_average': None,
            'daily_forecast': [],
            'monthly_value': None,
            'volatility': None,
            'history': [],
        }

    mean = sum(actuals) / len(actuals)
    variance = sum((value - mean) ** 2 for value in actuals) / len(actuals)
    volatility_ratio = variance ** 0.5 / mean if mean else 0
    volatility = (
        'high' if volatility_ratio >= 0.3
        else 'medium' if volatility_ratio >= 0.15
        else 'low'
    )

    return {
        'model': {
            'status': 'baseline',
            'title': 'Recent Sales Baseline',
            'message': (
                'Uses the average revenue per day over the latest 7 '
                'completed days, based on deduplicated recorded orders. '
                'This is a simple baseline, not a trained ML model.'
            ),
        },
        'daily_average': round(daily_average, 2),
        'daily_forecast': [
            round(daily_average, 2) for _ in range(horizon_days)
        ],
        'monthly_value': round(daily_average * 30, 2),
        'volatility': volatility,
        'history': history,
    }
