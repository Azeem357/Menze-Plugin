from rest_framework import serializers
from .models import AISuggestion

class AISuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISuggestion
        fields = '__all__'