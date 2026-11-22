from django.core.management.base import BaseCommand
import requests
from analytics.models import SessionEvent
from datetime import datetime

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        url = 'https://menze-store-backend-1.onrender.com/api/orders/sync/'
        response = requests.get(url)
        orders = response.json()
        
        for order in orders:
            # Create purchase event if not exists
            SessionEvent.objects.get_or_create(
                event_type='purchase',
                defaults={
                    'session_id': f"order-{order['order_id']}",
                    'store_id': 'menz-store',
                    'data': {
                        'order_id': order['order_id'],
                        'total': order['total'],
                        'items': order['items'],
                        'created_at': order['created_at'],
                    },
                    'timestamp': datetime.fromisoformat(order['created_at']),
                }
            )
        self.stdout.write(f"Synced {len(orders)} orders")