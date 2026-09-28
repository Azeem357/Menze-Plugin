from django.db import models
import uuid

class AISuggestion(models.Model):
    
    TYPE_CHOICES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    suggestion_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    source = models.CharField(max_length=100)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    is_acted_on = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    acted_on_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'ai_suggestions'
        ordering = [
            'is_acted_on',
            '-created_at'
        ]
    
    def __str__(self):
        return f"{self.priority} - {self.title}"
