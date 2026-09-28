from django.urls import path
from . import views

urlpatterns = [
    # Event tracking
    path(
        'events/capture',
        views.CaptureEventView.as_view(),
        name='capture-event'
    ),
    path(
        'events/order-complete',
        views.OrderWebhookView.as_view(),
        name='order-webhook'
    ),
    path(
        'events/',
        views.EventListView.as_view(),
        name='event-list'
    ),
    path(
        'events/<uuid:pk>/',
        views.EventDetailView.as_view(),
        name='event-detail'
    ),
    
    # Metrics
    path(
        'metrics/',
        views.MetricListView.as_view(),
        name='metric-list'
    ),
    path(
        'metrics/<uuid:pk>/',
        views.MetricDetailView.as_view(),
        name='metric-detail'
    ),
    
    # Dashboard
    path(
        'dashboard/overview',
        views.DashboardOverviewView.as_view(),
        name='dashboard-overview'
    ),
    path(
        'dashboard/funnel',
        views.FunnelView.as_view(),
        name='funnel'
    ),
    path(
        'dashboard/calculate',
        views.CalculateMetricsView.as_view(),
        name='calculate-metrics'
    ),
]