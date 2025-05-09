import os
import time
import threading
import logging
import google.generativeai as genai
from django.conf import settings

# Simple document embedding and retrieval functions
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class QAService:
    """
    Simplified QA Service using Google's Generative AI directly.
    """
    _instance = None
    _initialized = False
    _initializing = False
    _lock = threading.Lock()
    _documents = []
    _document_embeddings = None
    _vectorizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QAService, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Initialize the service with document loading and embedding"""
        with self._lock:
            if self._initialized:
                return True
            if self._initializing:
                return False
            self._initializing = True
        
        try:
            start_time = time.time()
            logger.info("Starting QA Service initialization")
            
            # Configure the Google Generative AI
            genai.configure(api_key="AIzaSyASH5--Y0O-QeD8GsD6pCyPGAc3t5scATw")
            
            # Load documents from the docs directory
            docs_dir = os.path.join(settings.BASE_DIR, "docs")
            self._documents = self._load_documents(docs_dir)
            
            # Create a simple vectorizer for document retrieval
            self._vectorizer = TfidfVectorizer()
            if self._documents:
                self._document_embeddings = self._vectorizer.fit_transform([doc["content"] for doc in self._documents])
            
            self._initialized = True
            self._initializing = False
            
            total_time = time.time() - start_time
            logger.info(f"QA Service initialized successfully in {total_time:.2f} seconds")
            return True
            
        except Exception as e:
            self._initializing = False
            logger.error(f"Error initializing QA Service: {str(e)}")
            return False

    def _load_documents(self, directory):
        """Load all documents from a directory recursively"""
        documents = []
        
        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            documents.append({
                                "path": file_path,
                                "content": content
                            })
                    except Exception as e:
                        logger.warning(f"Error loading document {file}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error walking directory {directory}: {str(e)}")
        
        logger.info(f"Loaded {len(documents)} documents")
        return documents

    def _retrieve_relevant_documents(self, query, k=3):
        """Retrieve the k most relevant documents for a query"""
        if not self._documents or self._document_embeddings is None:
            return []
        
        # Create query embedding
        query_embedding = self._vectorizer.transform([query])
        
        # Calculate similarity
        similarities = cosine_similarity(query_embedding, self._document_embeddings)[0]
        
        # Get top k document indices
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        # Return relevant documents
        relevant_docs = [self._documents[i]["content"] for i in top_indices]
        return relevant_docs

    def get_answer(self, question, timeout=10):
        """Get an answer to a question using the Gemini model"""
        # Initialize if needed
        if not self._initialized and not self._initialize():
            return "The service is currently initializing. Please try again in a moment."
        
        try:
            start_time = time.time()
            
            # Limit question length
            if len(question) > 500:
                question = question[:500] + "..."
            
            # Retrieve relevant documents
            relevant_docs = self._retrieve_relevant_documents(question)
            context = "\n\n".join(relevant_docs)
            
            # Create the prompt with context
            prompt = f"Answer based on this context:\n{context}\n\nQuestion: {question}\nAnswer:"
            
            # Generate response using Gemini
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 256,
                    "top_p": 1
                }
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Question processed in {processing_time:.2f} seconds")
            
            return response.text
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            logger.error(error_msg)
            return "Sorry, an error occurred while processing your question. Please try a simpler question or try again later."

    def get_answer_with_model_choice(self, question, model="gemini", timeout=10):
        """Maintain backward compatibility with the original API"""
        try:
            answer = self.get_answer(question, timeout)
            
            if "service is currently initializing" in answer:
                return {
                    "answer": answer,
                    "model_used": "initializing",
                    "model_requested": "gemini",
                    "fallback_used": False
                }
                
            return {
                "answer": answer,
                "model_used": "gemini",
                "model_requested": "gemini",
                "fallback_used": False
            }

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "answer": "Sorry, the system is currently experiencing high load. Please try again shortly.",
                "model_used": "error",
                "model_requested": "gemini",
                "fallback_used": False,
                "error": str(e)
            }