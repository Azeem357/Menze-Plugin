from django.urls import path
from . import views

urlpatterns = [
    path(
        'suggestions/',
        views.SuggestionListView.as_view(),
        name='suggestion-list'
    ),
    path(
        'suggestions/create/',
        views.SuggestionCreateView.as_view(),
        name='suggestion-create'
    ),
    path(
        'suggestions/stats/',
        views.SuggestionStatsView.as_view(),
        name='suggestion-stats'
    ),
    path(
        'suggestions/<uuid:pk>/',
        views.SuggestionDetailView.as_view(),
        name='suggestion-detail'
    ),
    path(
        'suggestions/<uuid:pk>/mark-done/',
        views.MarkActedOnView.as_view(),
        name='suggestion-mark-done'
    ),
]