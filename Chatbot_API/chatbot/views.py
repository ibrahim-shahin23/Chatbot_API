from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Query
from .serializers import QuerySerializer, QueryInputSerializer
from .chat_service import QAService
from .async_tasks import start_background_processing
import logging
import time

logger = logging.getLogger(__name__)


class QueryAPIView(APIView):
    """
    API endpoint for submitting questions.
    Uses background processing for long questions.
    """
    def post(self, request):
        start_time = time.time()
        
        # Validate input
        serializer = QueryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get the question
        question = serializer.validated_data['question']
        
        # Log request
        logger.info(f"Received question: '{question[:50]}...' (length: {len(question)})")

        try:
            # Get QA service
            qa_service = QAService()
            
            # Check if service is initialized
            if not qa_service._initialized:
                # Try to initialize
                initialized = qa_service._initialize()
                if not initialized:
                    return Response({
                        "status": "initializing",
                        "message": "The service is currently starting up. Please try again in a moment."
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # For long questions, process in background
            if len(question) > 100:
                question_id = f"q_{int(time.time())}"
                
                # Start background processing
                start_background_processing(question_id, question)
                
                return Response({
                    "status": "processing",
                    "message": "Your question is being processed. Please check the history endpoint in a few seconds.",
                    "question_id": question_id
                }, status=status.HTTP_202_ACCEPTED)
            
            # For shorter questions, process immediately
            result = qa_service.get_answer_with_model_choice(question, timeout=5)

            # Save to database
            query = Query(
                question=question,
                answer=result['answer'],
                model_requested="gemini",
                model_used="gemini",
                fallback_used=False
            )
            query.save()

            # Log performance
            processing_time = time.time() - start_time
            logger.info(f"Request processed in {processing_time:.2f} seconds")

            # Return response
            response_serializer = QuerySerializer(query)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error in QueryAPIView after {processing_time:.2f} seconds: {str(e)}")
            return Response({
                "error": "An error occurred while processing your request",
                "message": "Please try again with a simpler question"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QueryHistoryAPIView(APIView):
    """
    API endpoint for retrieving query history.
    Optimized with pagination and filtering.
    """
    def get(self, request):
        try:
            # Get pagination parameters
            limit = int(request.query_params.get('limit', 10))
            offset = int(request.query_params.get('offset', 0))
            
            # Limit to reasonable values
            limit = min(max(limit, 1), 50)
            
            # Get queries with pagination
            queries = Query.objects.all()[offset:offset+limit]
            
            # Get total count for pagination info
            total_count = Query.objects.count()
            
            serializer = QuerySerializer(queries, many=True)
            
            return Response({
                "results": serializer.data,
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            })
            
        except Exception as e:
            logger.error(f"Error in QueryHistoryAPIView: {str(e)}")
            return Response({
                "error": "An error occurred while retrieving query history"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QueryStatusAPIView(APIView):
    """
    API endpoint for checking the status of a specific query.
    """
    def get(self, request, question_id):
        try:
            # Try to find the query in the database by matching the start of the question
            # This is a rough approximation since we don't store question_id directly
            queries = Query.objects.filter(question__contains=question_id).order_by('-timestamp')
            
            if queries.exists():
                query = queries.first()
                serializer = QuerySerializer(query)
                return Response({
                    "status": "completed",
                    "query": serializer.data
                })
            else:
                return Response({
                    "status": "processing",
                    "message": "Your question is still being processed or wasn't found."
                }, status=status.HTTP_202_ACCEPTED)
                
        except Exception as e:
            logger.error(f"Error in QueryStatusAPIView: {str(e)}")
            return Response({
                "error": "An error occurred while checking query status"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)