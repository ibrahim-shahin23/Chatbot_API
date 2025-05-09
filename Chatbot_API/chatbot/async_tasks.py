import threading
from .chat_service import QAService
from .models import Query
import logging
import time

logger = logging.getLogger(__name__)

def process_query_in_background(question_id, question):
    """
    Process a query in a background thread.
    This allows the web request to return quickly while processing continues.
    
    Args:
        question_id: An identifier for the question
        question: The question text to process
    """
    logger.info(f"Starting background processing for question_id: {question_id}")
    start_time = time.time()
    
    try:
        # Get answer from QA service
        qa_service = QAService()
        result = qa_service.get_answer_with_model_choice(question, timeout=30)
        
        # Save to database
        query = Query(
            question=question,
            answer=result['answer'],
            model_requested="gemini",
            model_used="gemini",
            fallback_used=False
        )
        query.save()
        
        processing_time = time.time() - start_time
        logger.info(f"Background processing completed in {processing_time:.2f} seconds for question_id: {question_id}")
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error in background processing after {processing_time:.2f} seconds for question_id: {question_id}: {str(e)}")


def start_background_processing(question_id, question):
    """
    Start processing a query in a background thread.
    
    Args:
        question_id: An identifier for the question
        question: The question text to process
    """
    thread = threading.Thread(
        target=process_query_in_background,
        args=(question_id, question),
        daemon=True
    )
    thread.start()
    return thread