from django.urls import path
from . import views

urlpatterns = [
    path(
        'campaigns/',
        views.CampaignListCreateView.as_view(),
        name='campaign-list-create'
    ),
    path(
        'campaigns/<uuid:pk>/',
        views.CampaignDetailView.as_view(),
        name='campaign-detail'
    ),
    path(
        'campaigns/<uuid:pk>/update-spend/',
        views.CampaignUpdateSpendView.as_view(),
        name='campaign-update-spend'
    ),
]