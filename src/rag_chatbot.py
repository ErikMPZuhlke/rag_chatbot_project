import json
import logging
import ollama
from sys import stdout
from neo4j import GraphDatabase
from fastapi import FastAPI
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from retrieval.vector_search import EnhancedVectorRetriever
from retrieval.graph_search import GraphRetriever
from prompting.HyDE import HYDE_SYSTEM_PROMPT, FINAL_RESPONSE_PROMPT

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stdout)
    ]
)
logger = logging.getLogger("rag_chatbot")

# Initialize FastAPI
app = FastAPI()

# Connect to Neo4j
try:
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    logger.info("Successfully connected to Neo4j")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {e}")
    driver = None

# Load ChromaDB
try:
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="./db", embedding_function=embedding_model)
    logger.info("Successfully loaded ChromaDB")
except Exception as e:
    logger.error(f"Failed to load ChromaDB: {e}")
    vector_db = None

# Initialize retrievers
graph_retriever = GraphRetriever(driver, HYDE_SYSTEM_PROMPT)

@app.get("/query/")
async def query_llm(user_question: str):
    """Retrieve related methods/classes & vector search snippets."""
    try:
        logger.info(f"Received query endpoint request: {user_question}")
        
        # Stage 1: Get structured data from Neo4j using HyDE
        neo4j_results = graph_retriever.fetch_related_code(user_question)
        logger.debug(f"Neo4j results: {json.dumps(neo4j_results, default=str)[:500]}...")
        
        # Process Neo4j results and prepare for ChromaDB
        method_names = []
        class_names = []
        method_docstrings = []  # New list to store method docstrings
        graph_context_items = []
        
        # Limit the number of items from Neo4j results to control token size
        for item in neo4j_results:
            if "Method" in item:
                method_names.append(item["Method"])
                if "Documentation" in item:
                    method_docstrings.append(item["Documentation"])
            if "Class" in item:
                class_names.append(item["Class"])

            # Create a human-readable summary of each result
            item_summary = []
            for key, value in item.items():
                if value and isinstance(value, str):  # Check if value exists and is a string
                    item_summary.append(f"{key}: {value}")
            
            if item_summary:
                graph_context_items.append("\n".join(set(item_summary)))  # Use set to avoid duplicates
        
        # Join all text summaries
        graph_context = "\n\n".join(graph_context_items)
        logger.debug(f"Graph context length: {len(graph_context)} characters")
        
        # Stage 2: Use the EnhancedVectorRetriever for vector search
        vector_retriever = EnhancedVectorRetriever(vector_db)
        
        # Perform the retrieval with semantic enrichment and metadata filtering
        vector_results, enhanced_query = vector_retriever.retrieve(
            user_question,
            method_names,
            class_names,
            method_docstrings,
            k=7
        )
        
        # Format the results for the final prompt
        vector_context = vector_retriever.format_results(vector_results)
        
        # Format the final prompt with separate sections for graph and vector contexts
        try:
            prompt = FINAL_RESPONSE_PROMPT.format(
                graph_context=graph_context, 
                vector_context=vector_context,
                user_question=user_question
            )

            logger.debug(f"Final prompt length: {len(prompt)} characters")

        except KeyError as e:
            logger.error(f"Format error in FINAL_RESPONSE_PROMPT: {e}")
            logger.debug(f"FINAL_RESPONSE_PROMPT placeholders: {[ph for ph in FINAL_RESPONSE_PROMPT if '{' in ph and '}' in ph]}")
            # Fallback to f-string if format fails
            prompt = f"{FINAL_RESPONSE_PROMPT}\n\nGraph Context:\n{graph_context}\n\nVector Context:\n{vector_context}\n\nUser Question: {user_question}"
        
        # Get response from LLM
        logger.info("Requesting final response from Mistral")
        response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
        result = {"answer": response["message"]["content"]}

        logger.info("Successfully generated response")
        logger.debug(f"Response length: {len(result['answer'])} characters")
        
        return result
    
    except Exception as e:
        logger.error(f"Error in query_llm: {e}", exc_info=True)
        return {"answer": f"An error occurred: {str(e)}. Please check the logs for more details."}

# For direct testing
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server in debug mode")
    uvicorn.run(app, host="0.0.0.0", port=8000)