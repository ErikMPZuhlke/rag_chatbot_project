import logging
import ollama
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional

logger = logging.getLogger("rag_chatbot.graph_search")

class GraphRetriever:
    """A class for retrieving code information from Neo4j using HyDE approach."""
    
    def __init__(self, driver: GraphDatabase.driver, hyde_system_prompt: str):
        """
        Initialize the GraphRetriever.
        
        Args:
            driver: Neo4j database driver
            hyde_system_prompt: System prompt for HyDE query generation
        """
        self.driver = driver
        self.hyde_system_prompt = hyde_system_prompt
    
    def fetch_related_code(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Query Neo4j for methods/classes related to the user query using HyDE approach.
        
        Args:
            user_query: User's natural language question
            
        Returns:
            List of dictionaries containing Neo4j query results
        """
        try:
            # Log the user query
            logger.info(f"Processing query: {user_query}")
            
            # Generate Cypher query using HyDE approach
            cypher_query = self._generate_cypher_query(user_query)
            
            if not cypher_query:
                logger.error("Failed to generate a valid Cypher query")
                return []
            
            # Execute the Cypher query
            return self._execute_cypher_query(cypher_query)
            
        except Exception as e:
            logger.error(f"Error in fetch_related_code: {e}", exc_info=True)
            return []
    
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
        
        return True
    
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
        WHERE m.name CONTAINS "{search_term}" OR m.docstring CONTAINS "{search_term}" 
        MATCH (c:Class)-[:CONTAINS]->(m)
        MATCH (n:Namespace)-[:CONTAINS]->(c)
        RETURN n.name AS Namespace, c.name AS Class, m.name AS Method
        LIMIT 5
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