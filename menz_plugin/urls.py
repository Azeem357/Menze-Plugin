from django.contrib import admin
from django.urls import path, include
from analytics.views import ServeTrackerView

urlpatterns = [
    # Django admin panel (free!)
    path('admin/', admin.site.urls),
    
    # Serve tracking script
    path('tracker.js', ServeTrackerView.as_view()),
    
    # API routes
    path('api/', include('analytics.urls')),
    path('api/', include('campaigns.urls')),
    path('api/', include('suggestions.urls')),
]