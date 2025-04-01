import logging
import ollama
import json
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional

logger = logging.getLogger("rag_chatbot.graph_search")

class GraphRetriever:
    """A class for retrieving code information from Neo4j using HyDE approach."""
    
    def __init__(self, driver: GraphDatabase.driver, hyde_system_prompt: str, hyde_refinement_prompt: str = None):
        """
        Initialize the GraphRetriever.
        
        Args:
            driver: Neo4j database driver
            hyde_system_prompt: System prompt for HyDE query generation
            hyde_refinement_prompt: System prompt for refining queries based on initial results
        """
        self.driver = driver
        self.hyde_system_prompt = hyde_system_prompt
        self.hyde_refinement_prompt = hyde_refinement_prompt
        
    def fetch_related_code(self, user_query: str, use_refinement: bool = True) -> List[Dict[str, Any]]:
        """
        Query Neo4j for methods/classes related to the user query using HyDE approach.
        
        Args:
            user_query: User's natural language question
            use_refinement: Whether to use query refinement (two-stage approach)
            
        Returns:
            List of dictionaries containing Neo4j query results
        """
        try:
            # Log the user query
            logger.info(f"Processing query: {user_query}")
            
            # First stage: Generate initial Cypher query using HyDE approach
            initial_query = self._generate_cypher_query(user_query)
            
            if not initial_query:
                logger.error("Failed to generate a valid Cypher query")
                return []
            
            # Execute the initial Cypher query
            initial_results = self._execute_cypher_query(initial_query)
            
            # If refinement is enabled and we have a refinement prompt
            if use_refinement and self.hyde_refinement_prompt and initial_query:
                # Check if refinement is needed based on results
                if self._should_refine_query(initial_results, user_query):
                    # Generate a refined query
                    refined_query = self._refine_cypher_query(
                        user_query, 
                        initial_query, 
                        initial_results
                    )
                    
                    if refined_query and refined_query != initial_query:
                        logger.info(f"Using refined query: {refined_query}")
                        # Execute the refined query
                        refined_results = self._execute_cypher_query(refined_query)
                        
                        # If refined query returned results, use those instead
                        if refined_results:
                            logger.info(f"Refined query returned {len(refined_results)} results")
                            return refined_results
                
                # Return initial results if refinement didn't happen or didn't help
                return initial_results
            else:
                # Return initial results if refinement is disabled
                return initial_results
            
        except Exception as e:
            logger.error(f"Error in fetch_related_code: {e}", exc_info=True)
            return []
    
    def _should_refine_query(self, results: List[Dict], user_query: str) -> bool:
        """Determine if query refinement is needed based on initial results."""
        # Refine if no results
        if not results:
            logger.info("No results from initial query - refinement needed")
            return True
            
        # Check if results are likely related to the user query
        # This is a simple heuristic - could be made more sophisticated
        query_terms = set(user_query.lower().split())
        result_terms = set()
        
        # Extract terms from results
        for result in results[:5]:  # Check first 5 results
            for value in result.values():
                if isinstance(value, str):
                    result_terms.update(value.lower().split())
        
        # Calculate overlap between query terms and result terms
        overlap = query_terms.intersection(result_terms)
        overlap_ratio = len(overlap) / len(query_terms) if query_terms else 0
        
        # If overlap ratio is low, refine the query
        if overlap_ratio < 0.3:  # Threshold can be adjusted
            logger.info(f"Low term overlap ({overlap_ratio:.2f}) - refinement needed")
            return True
            
        return False
    
    def _refine_cypher_query(self, user_query: str, initial_query: str, initial_results: List[Dict]) -> Optional[str]:
        """Refine a Cypher query based on initial results."""
        try:
            # Prepare sample results for the prompt
            sample_results_str = json.dumps(initial_results[:3], indent=2) if initial_results else "No results"
            
            # Create refinement prompt
            refinement_prompt = self.hyde_refinement_prompt.format(
                user_question=user_query,
                initial_query=initial_query,
                result_count=len(initial_results),
                sample_results=sample_results_str
            )
            
            logger.info("Generating refined Cypher query")
            response = ollama.chat(model="codestral", messages=[{"role": "user", "content": refinement_prompt}])
            refined_query = response["message"]["content"].strip()
            
            # Clean up the refined query
            if "```" in refined_query:
                parts = refined_query.split("```")
                if len(parts) >= 3:
                    refined_query = parts[1]
                    if refined_query.startswith("cypher"):
                        refined_query = refined_query[6:]
                    refined_query = refined_query.strip()
            
            # Validate the refined query
            if self._validate_cypher_query(refined_query) and refined_query != initial_query:
                logger.info(f"Successfully refined query: {refined_query}")
                return refined_query
            else:
                logger.info("Refined query validation failed or no change - using initial query")
                return initial_query
                
        except Exception as e:
            logger.error(f"Error refining Cypher query: {e}")
            return initial_query  # Fall back to the initial query
    
    def _generate_cypher_query(self, user_query: str) -> Optional[str]:
        """
        Generate a Cypher query using HyDE approach.
        
        Args:
            user_query: User's natural language question
            
        Returns:
            Generated Cypher query or None if generation failed
        """
        try:
            # Combine the system prompt with the user query to generate a Cypher query
            hyde_prompt = f"{self.hyde_system_prompt}\n\nUser question: {user_query}"
            logger.debug(f"HyDE prompt length: {len(hyde_prompt)} characters")
            
            # Get the Cypher query from the LLM
            logger.info("Requesting Cypher query from Codestral")
            response = ollama.chat(model="codestral", messages=[{"role": "user", "content": hyde_prompt}])
            cypher_query = response["message"]["content"].strip()
            
            # Extract just the Cypher query (remove any explanations)
            if "```" in cypher_query:
                # Extract code between backticks if present
                parts = cypher_query.split("```")
                if len(parts) >= 3:  # Proper code block with start and end ticks
                    cypher_query = parts[1]
                    if cypher_query.startswith("cypher"):
                        cypher_query = cypher_query[6:]  # Remove "cypher" language identifier
                    cypher_query = cypher_query.strip()
            
            logger.info(f"Generated Cypher query: {cypher_query}")
            
            # Basic validation of the query
            if not self._validate_cypher_query(cypher_query):
                logger.warning("Generated Cypher query failed validation")
                cypher_query = self._generate_fallback_query(user_query)
                logger.info(f"Using fallback query: {cypher_query}")
            
            return cypher_query
            
        except Exception as e:
            logger.error(f"Error generating Cypher query: {e}", exc_info=True)
            return self._generate_fallback_query(user_query)
    
    def _validate_cypher_query(self, cypher_query: str) -> bool:
        """
        Perform basic validation on a Cypher query.
        
        Args:
            cypher_query: Cypher query to validate
            
        Returns:
            True if query appears to be valid, False otherwise
        """
        # Check for required Cypher components
        required_keywords = ["MATCH", "RETURN", "LIMIT"]
        if not all(keyword in cypher_query.upper() for keyword in required_keywords):
            logger.warning("Query validation failed: missing required components")
            return False
        
        # Check for invalid property references
        invalid_properties = ["description", "comments", "content", "body", "type"]
        for prop in invalid_properties:
            if f".{prop}" in cypher_query:
                logger.warning(f"Query validation failed: contains invalid property '{prop}'")
                return False
        
        # Check if query uses case-insensitive matching with toLower() - add this
        if ("CONTAINS" in cypher_query.upper() or "STARTS WITH" in cypher_query.upper()) and "toLower" not in cypher_query:
            logger.info("Enhancing query with case-insensitive matching")
            return self._enhance_with_case_insensitivity(cypher_query)
        
        return True
    
    def _enhance_with_case_insensitivity(self, cypher_query: str) -> str:
        """Add case-insensitive matching to a query that doesn't have it."""
        # This is a simple implementation - a more robust version would use a parser
        modified_query = cypher_query
        
        # Replace string comparisons with case-insensitive versions
        import re
        
        # Pattern for string comparisons in WHERE clauses
        patterns = [
            (r'(WHERE\s+)(\w+\.\w+)\s+CONTAINS\s+(["\'])(.+?)(["\'])', 
             r'\1toLower(\2) CONTAINS toLower(\3\4\5)'),
            (r'(WHERE\s+)(\w+\.\w+)\s+STARTS\s+WITH\s+(["\'])(.+?)(["\'])', 
             r'\1toLower(\2) STARTS WITH toLower(\3\4\5)'),
            (r'(OR\s+)(\w+\.\w+)\s+CONTAINS\s+(["\'])(.+?)(["\'])', 
             r'\1toLower(\2) CONTAINS toLower(\3\4\5)')
        ]
        
        for pattern, replacement in patterns:
            modified_query = re.sub(pattern, replacement, modified_query, flags=re.IGNORECASE)
        
        logger.info(f"Enhanced query with case-insensitivity: {modified_query}")
        return modified_query
    
    def _generate_fallback_query(self, user_query: str) -> str:
        """
        Generate a simple, reliable fallback query based on user input.
        
        Args:
            user_query: User's natural language question
            
        Returns:
            A simple Cypher query that's unlikely to fail
        """
        # Extract potential keywords from user query
        keywords = user_query.split()
        search_term = ""
        
        # Use longest word as potential class/method name (simple heuristic)
        if keywords:
            search_term = max(keywords, key=len)
            if len(search_term) < 3:  # If all words are very short, use the whole query
                search_term = user_query
        
        # Safe, simple query that's unlikely to fail
        return f"""
        MATCH (m:Method)
        WHERE toLower(m.name) CONTAINS toLower("{search_term}") OR toLower(m.docstring) CONTAINS toLower("{search_term}") 
        MATCH (c:Class)-[:CONTAINS]->(m)
        MATCH (n:Namespace)-[:CONTAINS]->(c)
        RETURN n.name AS Namespace, c.name AS Class, m.name AS Method
        LIMIT 50
        """
    
    def _execute_cypher_query(self, cypher_query: str) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query against Neo4j and process the results.
        
        Args:
            cypher_query: Cypher query to execute
            
        Returns:
            List of dictionaries containing query results
        """
        if self.driver is None:
            logger.error("Neo4j driver not initialized")
            return []
            
        try:
            with self.driver.session() as session:
                logger.debug("Executing Cypher query")
                results = session.run(cypher_query)
                
                # Convert results to a more structured format for analysis
                code_items = []
                for record in results:
                    # Create a structured dictionary from the record
                    item = {}
                    for key in record.keys():
                        item[key] = record[key]
                    code_items.append(item)
                
                logger.info(f"Neo4j returned {len(code_items)} results")
                return code_items
                
        except Exception as db_error:
            logger.error(f"Neo4j query execution failed: {db_error}")
            # Try with simpler fallback if original query failed
            try:
                cypher_query = self._generate_fallback_query(user_query="code")
                logger.info(f"Trying simple fallback query: {cypher_query}")
                with self.driver.session() as session:
                    results = session.run(cypher_query)
                    code_items = []
                    for record in results:
                        item = {}
                        for key in record.keys():
                            item[key] = record[key]
                        code_items.append(item)
                    return code_items
            except Exception as e:
                logger.error(f"Fallback query also failed: {e}")
                return []