from django.contrib import admin
from .models import AISuggestion

@admin.register(AISuggestion)
class AISuggestionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'suggestion_type',
        'priority', 'is_acted_on', 'created_at'
    ]
    list_filter = [
        'suggestion_type', 'priority', 'is_acted_on'
    ]
