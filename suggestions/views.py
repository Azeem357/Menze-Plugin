from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import AISuggestion
from .serializers import AISuggestionSerializer


class SuggestionListView(generics.ListAPIView):
    """
    GET /api/suggestions/
    List all suggestions with optional filters
    """
    queryset = AISuggestion.objects.all()
    serializer_class = AISuggestionSerializer
    
    def get_queryset(self):
        queryset = AISuggestion.objects.all()
        
        # Filter by type: internal or external
        suggestion_type = self.request.query_params\
            .get('type')
        if suggestion_type:
            queryset = queryset.filter(
                suggestion_type=suggestion_type
            )
        
        # Filter by priority: high, medium, low
        priority = self.request.query_params.get(
            'priority'
        )
        if priority:
            queryset = queryset.filter(
                priority=priority
            )
        
        # Filter active (not acted on)
        active = self.request.query_params.get('active')
        if active == 'true':
            queryset = queryset.filter(
                is_acted_on=False
            )
        
        return queryset.order_by(
            'is_acted_on', '-created_at'
        )


class SuggestionCreateView(generics.CreateAPIView):
    """
    POST /api/suggestions/
    Create new suggestion (used by AI agent)
    """
    queryset = AISuggestion.objects.all()
    serializer_class = AISuggestionSerializer


class SuggestionDetailView(
    generics.RetrieveDestroyAPIView
):
    """
    GET    /api/suggestions/<id>/
    DELETE /api/suggestions/<id>/
    """
    queryset = AISuggestion.objects.all()
    serializer_class = AISuggestionSerializer


class MarkActedOnView(APIView):
    """
    POST /api/suggestions/<id>/mark-done/
    Owner marks suggestion as acted on.
    Custom logic → APIView needed
    """
    def post(self, request, pk):
        try:
            suggestion = AISuggestion.objects.get(pk=pk)
        except AISuggestion.DoesNotExist:
            return Response(
                {'error': 'Suggestion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        suggestion.is_acted_on = True
        suggestion.acted_on_at = timezone.now()
        suggestion.save()
        
        return Response({
            'success': True,
            'message': 'Marked as acted on',
            'suggestion': AISuggestionSerializer(
                suggestion
            ).data
        })


class SuggestionStatsView(APIView):
    """
    GET /api/suggestions/stats/
    Returns suggestion summary counts.
    Custom aggregation → APIView needed
    """
    def get(self, request):
        total = AISuggestion.objects.count()
        active = AISuggestion.objects.filter(
            is_acted_on=False
        ).count()
        acted_on = AISuggestion.objects.filter(
            is_acted_on=True
        ).count()
        high = AISuggestion.objects.filter(
            priority='high',
            is_acted_on=False
        ).count()
        medium = AISuggestion.objects.filter(
            priority='medium',
            is_acted_on=False
        ).count()
        low = AISuggestion.objects.filter(
            priority='low',
            is_acted_on=False
        ).count()
        
        return Response({
            'total': total,
            'active': active,
            'acted_on': acted_on,
            'by_priority': {
                'high': high,
                'medium': medium,
                'low': low
            }
        })
