from django.db import models

class Query(models.Model):
    """
    Model for storing query interactions.
    All queries now use the Gemini model.
    """
    question = models.TextField()
    answer = models.TextField()
    model_requested = models.CharField(max_length=50, default="gemini")
    model_used = models.CharField(max_length=50, default="gemini")
    fallback_used = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"Query {self.id}: {self.question[:50]}..."