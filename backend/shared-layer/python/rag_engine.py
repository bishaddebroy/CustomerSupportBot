import logging
import time
from typing import List, Dict, Any

class RAGEngine:
    """
    Retrieval-Augmented Generation Engine
    Combines vector search with QA model to extract answers
    """
    
    def __init__(self, llm_handler, vector_store):
        """
        Initialize the RAG engine
        
        Args:
            llm_handler: Handler for the QA model
            vector_store: Vector database for document storage/retrieval
        """
        self.llm_handler = llm_handler
        self.vector_store = vector_store
        self.logger = logging.getLogger(__name__)
    
    def process_query(self, query: str, session_id: str = "default") -> str:
        """
        Process a user query through the RAG pipeline
        
        Args:
            query: The user's question
            session_id: Session identifier for conversation tracking
            
        Returns:
            Answer extracted from relevant documents
        """
        start_time = time.time()
        self.logger.info(f"Processing query: {query}")
        
        try:
            # Step 1: Retrieve relevant documents from vector store
            retrieved_docs = self.retrieve_relevant_documents(query)
            self.logger.debug(f"Retrieved {len(retrieved_docs)} relevant documents")
            
            if not retrieved_docs:
                return "I couldn't find any relevant information to answer your question."
            
            # Step 2: Filter documents by relevance - only use documents with similarity above threshold
            similarity_threshold = 0.5  # Adjust this value based on testing
            relevant_docs = [doc for doc in retrieved_docs if doc.get('similarity', 0) > similarity_threshold]
            
            # If no documents pass the threshold, use just the top document
            if not relevant_docs and retrieved_docs:
                relevant_docs = [retrieved_docs[0]]
                
            self.logger.debug(f"Using {len(relevant_docs)} documents above relevance threshold")
            
            # Step 3: Check for corrupted content
            clean_docs = []
            for doc in relevant_docs:
                content = doc.get('content', '')
                # If content is mostly unprintable or very short, skip it
                if self._is_valid_content(content):
                    clean_docs.append(doc)
            
            # If all documents were filtered out, return a message
            if not clean_docs:
                return "I found some relevant information, but it appears to be in an unsupported format."
            
            # Step 4: Prepare context from filtered documents
            context = self.prepare_context(clean_docs)
            
            # Step 5: Extract answer using QA model
            answer = self.llm_handler.generate(query, context)
            
            # Log processing time for monitoring
            processing_time = time.time() - start_time
            self.logger.info(f"Query processed in {processing_time:.2f} seconds")
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Error in RAG processing: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error processing your question. Please try again."
    
    def retrieve_relevant_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the vector store
        
        Args:
            query: The user's question
            top_k: Number of top documents to retrieve
            
        Returns:
            List of relevant document chunks with metadata
        """
        # Retrieve documents from vector store
        results = self.vector_store.search(query, top_k=top_k)
        
        # Process and return results
        return results
    
    def prepare_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from retrieved documents
        
        Args:
            documents: List of retrieved document chunks
            
        Returns:
            Formatted context string
        """
        if not documents:
            return "No relevant information found."
            
        # For QA model, join all document content into a single context
        # The model will extract the answer from this context
        context_parts = []
        
        for doc in documents:
            content = doc.get('content', '')
            context_parts.append(content)
            
        return " ".join(context_parts)
    
    def _is_valid_content(self, content: str) -> bool:
        """
        Check if content appears to be valid text
        
        Args:
            content: Text content to validate
            
        Returns:
            Boolean indicating if content is valid
        """
        # Check if string is empty or too short
        if not content or len(content) < 5:
            return False
        
        # Check if more than 80% of characters are printable
        printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
        if printable_chars / len(content) < 0.8:
            return False
        
        # Check if content has mostly alphanumeric characters
        if sum(c.isalnum() for c in content) / len(content) < 0.3:
            return False
            
        return True