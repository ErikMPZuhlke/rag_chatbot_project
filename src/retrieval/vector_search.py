import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain.vectorstores import Chroma
from langchain.schema import Document

logger = logging.getLogger("rag_chatbot.vector_search")

class EnhancedVectorRetriever:
    """A specialized retriever that enhances queries with metadata from Neo4j and uses filters."""
    
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
    
    def retrieve(self, 
                 user_question: str, 
                 method_names: List[str] = None,
                 class_names: List[str] = None,
                 method_docstrings: List[str] = None,
                 k: int = 3) -> Tuple[List[Document], str]:
        """
        Perform enhanced vector retrieval using Neo4j metadata.
        
        Args:
            user_question: Original user query
            method_names: List of method names from Neo4j
            class_names: List of class names from Neo4j
            method_docstrings: List of method docstrings from Neo4j
            k: Number of results to retrieve
            
        Returns:
            Tuple containing (vector_results, enhanced_query)
        """
        method_names = method_names or []
        class_names = class_names or []
        method_docstrings = method_docstrings or []
        
        # Create enhanced query with semantic context
        enhanced_query = self._build_enhanced_query(
            user_question, 
            method_names, 
            class_names, 
            method_docstrings
        )
        
        # Retrieve results with metadata filtering
        vector_results = self._retrieve_with_filters(
            enhanced_query,
            method_names,
            class_names,
            k
        )
        
        logger.info(f"Vector search returned {len(vector_results)} results")
        return vector_results, enhanced_query
    
    def _build_enhanced_query(self, 
                             user_question: str,
                             method_names: List[str],
                             class_names: List[str],
                             method_docstrings: List[str]) -> str:
        """Build an enhanced query combining original query with semantic context."""
        # Start with original user question
        enhanced_query = user_question
        
        # Create a semantic-rich enhanced query
        semantic_enhancements = []
        
        # Add entity names (method names and class names)
        if method_names:
            semantic_enhancements.extend(method_names)
        if class_names:
            semantic_enhancements.extend(class_names)
        
        # Add method docstrings (but limit their length to avoid overwhelming the query)
        for docstring in method_docstrings:
            # Extract the first sentence or up to 100 characters from each docstring
            if docstring:
                first_sentence = docstring.split('.')[0] if '.' in docstring else docstring
                if len(first_sentence) > 100:
                    first_sentence = first_sentence[:100]
                semantic_enhancements.append(first_sentence)
        
        # Add all enhancements to the query, but avoid making it too long
        if semantic_enhancements:
            # Join all enhancements but limit total length
            enhancements_text = " ".join(set(semantic_enhancements)) # Use set to avoid duplicates
            if len(enhancements_text) > 500:  # Reasonable limit for embedding models
                enhancements_text = enhancements_text[:500]
            enhanced_query += " " + enhancements_text
        
        logger.info(f"Enhanced query for vector search: {enhanced_query[:100]}...")  # Log first 100 chars
        return enhanced_query
    
    def _retrieve_with_filters(self,
                              enhanced_query: str,
                              method_names: List[str], 
                              class_names: List[str],
                              k: int) -> List[Document]:
        """Retrieve documents using metadata filtering based on Neo4j results."""
        try:
            # Now implement metadata filtering for more precise results
            if method_names or class_names:
                logger.info("Using metadata filters from Neo4J results")
                
                # Case 1: If we have both method and class names
                if method_names and class_names:
                    return self._retrieve_with_method_and_class_filters(
                        enhanced_query, method_names, class_names, k
                    )
                
                # Case 2: If we only have method names
                elif method_names:
                    return self._retrieve_with_method_filters(
                        enhanced_query, method_names, k
                    )
                
                # Case 3: If we only have class names
                elif class_names:
                    return self._retrieve_with_class_filters(
                        enhanced_query, class_names, k
                    )
            
            # Standard similarity search if we don't have metadata
            return self.vector_db.similarity_search(enhanced_query, k=k)
            
        except Exception as e:
            logger.error(f"Error in vector retrieval: {e}", exc_info=True)
            # Fall back to standard search without filters
            logger.info("Falling back to standard search without filters")
            return self.vector_db.similarity_search(enhanced_query, k=k)
    
    def _retrieve_with_method_and_class_filters(self,
                                               enhanced_query: str,
                                               method_names: List[str],
                                               class_names: List[str],
                                               k: int) -> List[Document]:
        """Retrieve with both method and class filters."""
        try:
            # First try to find exact matches with both filters
            filter_conditions = {
                "$and": [
                    {"method_name": {"$in": method_names}},
                    {"class_name": {"$in": class_names}}
                ]
            }
            
            vector_results = self.vector_db.similarity_search(
                enhanced_query,
                k=k,
                filter=filter_conditions
            )
            
            # If no results, fall back to OR condition
            if not vector_results:
                filter_conditions = {
                    "$or": [
                        {"method_name": {"$in": method_names}},
                        {"class_name": {"$in": class_names}}
                    ]
                }
                vector_results = self.vector_db.similarity_search(
                    enhanced_query,
                    k=k,
                    filter=filter_conditions
                )
            
            return vector_results
            
        except Exception as e:
            logger.error(f"Error with combined method/class filtering: {e}")
            # Fall back to standard search
            return self.vector_db.similarity_search(enhanced_query, k=k)
    
    def _retrieve_with_method_filters(self,
                                     enhanced_query: str,
                                     method_names: List[str],
                                     k: int) -> List[Document]:
        """Retrieve with method name filters."""
        try:
            filter_conditions = {"method_name": {"$in": method_names}}
            return self.vector_db.similarity_search(
                enhanced_query,
                k=k,
                filter=filter_conditions
            )
        except Exception as e:
            logger.error(f"Error with method name filtering: {e}")
            return self.vector_db.similarity_search(enhanced_query, k=k)
    
    def _retrieve_with_class_filters(self,
                                    enhanced_query: str,
                                    class_names: List[str],
                                    k: int) -> List[Document]:
        """Retrieve with class name filters."""
        try:
            filter_conditions = {"class_name": {"$in": class_names}}
            return self.vector_db.similarity_search(
                enhanced_query,
                k=k,
                filter=filter_conditions
            )
        except Exception as e:
            logger.error(f"Error with class name filtering: {e}")
            return self.vector_db.similarity_search(enhanced_query, k=k)
    
    def format_results(self, vector_results: List[Document]) -> str:
        """Format vector results into a readable context string."""
        vector_snippets = []
        
        for i, doc in enumerate(vector_results):
            content = doc.page_content
            metadata = doc.metadata
            
            # Add metadata to content for context
            metadata_text = f"Method: {metadata.get('method_name', 'Unknown')} | Class: {metadata.get('class_name', 'Unknown')}"
            enriched_content = f"{metadata_text}\n\n{content}"
            
            logger.debug(f"Vector result {i+1} length: {len(enriched_content)} characters")
            
            # Truncate long vector results
            if len(enriched_content) > 800:
                enriched_content = enriched_content[:800] + " [content truncated...]"
            
            vector_snippets.append(enriched_content)
        
        vector_context = "\n\n---\n\n".join(vector_snippets)
        logger.debug(f"Vector context length: {len(vector_context)} characters")
        
        return vector_context