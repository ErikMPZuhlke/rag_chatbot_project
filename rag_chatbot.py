import ollama
from fastapi import FastAPI
from fastapi import FastAPI
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import logging

app = FastAPI()

# Load the same free embedding model
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory="./db", embedding_function=embedding_model)

@app.get("/query/")
async def query_llm(user_question: str):
    """Retrieves relevant code snippets and queries Ollama LLM."""
    
    # Retrieve relevant documents
    results = vector_db.similarity_search(user_question, k=3)
    
    context = "\n\n".join([doc.page_content for doc in results])

    # Query Ollama with RAG-enhanced prompt
    prompt = f"""
    You are an expert on a legacy codebase. Answer questions based on this code:
    
    {context}
    
    User question: {user_question}
    """
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)

    # Log the prompt
    logging.debug(f"Prompt sent to LLM: {prompt}")
    response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
    
    return {"answer": response["message"]["content"]}
