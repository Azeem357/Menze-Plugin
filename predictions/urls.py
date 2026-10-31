from django.urls import path
from .views import SalesPredictionView, RecommendationView

urlpatterns = [
    path('predict/sales/',       SalesPredictionView.as_view()),
    path('predict/recommend/',   RecommendationView.as_view()),
]