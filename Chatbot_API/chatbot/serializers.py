from rest_framework import serializers
from .models import Query

class QueryInputSerializer(serializers.Serializer):
    """
    Serializer for validating query inputs.
    Still accepts model parameter for backward compatibility but it's ignored.
    """
    question = serializers.CharField(required=True)
    model = serializers.CharField(required=False, default="gemini")


class QuerySerializer(serializers.ModelSerializer):
    """
    Serializer for Query model.
    Used for query responses and history endpoints.
    """
    class Meta:
        model = Query
        fields = ['id', 'question', 'answer', 'model_used', 'timestamp']