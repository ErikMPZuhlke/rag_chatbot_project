# RAG Chatbot Project

## Overview

This project implements a Retrieval-Augmented Generation (RAG) chatbot designed to assist with querying and understanding a legacy codebase. The chatbot uses modern machine learning techniques to retrieve relevant code snippets and provide context-aware answers to user questions.

### Key Features
- **Code Ingestion**: Processes and indexes the legacy codebase for efficient retrieval using both graph and vector databases.
- **Hybrid RAG Approach**: Combines Neo4j graph-based retrieval with ChromaDB vector search for comprehensive code understanding.
- **AST Processing**: Parses C# code using abstract syntax trees for structured code analysis.
- **Neo4j Integration**: Stores code relationships in Neo4j for graph-based querying.
- **FastAPI Integration**: Provides a RESTful API for querying the chatbot.
- **Streamlit UI**: A user-friendly web interface for interacting with the chatbot.

---

## Architecture

### 1. **Code Processing & Ingestion**
- **File**: `ingest.py` & `code_processing/ast_processing.py`
- **Purpose**: 
  - Parses C# code using Tree-sitter to extract namespaces, classes, and methods.
  - Builds a knowledge graph in Neo4j to represent code relationships.
  - Splits the code into manageable chunks for better retrieval.
  - Stores the processed data in ChromaDB using embeddings from the `sentence-transformers/all-MiniLM-L6-v2` model.

### 2. **Hybrid Retrieval System**
- **Files**: `retrieval/graph_search.py` & `retrieval/vector_search.py`
- **Purpose**:
  - `GraphRetriever`: Leverages Neo4j to retrieve code structures using Hypothetical Document Embedding (HyDE).
  - `EnhancedVectorRetriever`: Performs semantic search on code snippets with metadata filtering.
  - Combines structured (graph) and unstructured (vector) information for comprehensive retrieval.

### 3. **RAG Chatbot**
- **File**: `rag_chatbot.py`
- **Purpose**:
  - Orchestrates the retrieval process using both graph and vector stores.
  - Constructs a context-aware prompt using the retrieved information.
  - Uses the Ollama API with models like Mistral and Codestral to generate responses.
  - Implements logging for better debugging and troubleshooting.

### 4. **Streamlit UI**
- **File**: `ui/app.py`
- **Purpose**:
  - Provides a web-based user interface for interacting with the chatbot.
  - Allows users to input questions and view responses in a simple and intuitive format.
  - Communicates with the FastAPI backend to fetch answers.

---

## Prerequisites
1. **Python Environment**:
   - Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/).
   - Create and activate the Conda environment using the provided `environment.yml` file:
     ```bash
     conda env create -f environment.yml
     conda activate rag-chatbot
     ```
   - Alternatively, use pip with the requirements.txt file:
     ```bash
     pip install -r requirements.txt
     ```

2. **Neo4j Database**:
   - Install and run Neo4j (local instance or Docker).
   - Ensure Neo4j is accessible at bolt://localhost:7687 with default credentials.

3. **Ollama**:
   - Install Ollama to run local LLMs: https://ollama.com/
   - Pull required models:
     ```bash
     ollama pull mistral
     ollama pull codestral
     ```

4. **Legacy Codebase**:
   - Ensure the `legacy_code` folder contains the C# codebase you want to index and query.

---

## Steps to Run

#### 1. **Ingest the C# Codebase**
   - Run the `ingest.py` script to process and index the legacy codebase:
     ```bash
     python src/ingest.py
     ```
   - This will:
     - Parse the C# code using Tree-sitter
     - Store structure information in Neo4j
     - Create vector embeddings in ChromaDB under the `./db` folder

#### 2. **Start the Chatbot API**
   - Run the `rag_chatbot.py` script to start the FastAPI server:
     ```bash
     python src/rag_chatbot.py
     ```
   - Or using uvicorn directly:
     ```bash
     uvicorn src.rag_chatbot:app --reload
     ```
   - The API will be available at `http://localhost:8000`.

#### 3. **Launch the Streamlit UI**
   - Run the Streamlit app:
     ```bash
     streamlit run src/ui/app.py
     ```
   - The Streamlit app will open in your web browser where you can input questions about the codebase.

---

## Folder Structure

```
rag_chatbot_project/
├── src/
│   ├── code_processing/
│   │   └── ast_processing.py   # C# code parser using Tree-sitter
│   ├── prompting/
│   │   └── HyDE.py             # Prompt templates for HyDE and response generation
│   ├── retrieval/
│   │   ├── graph_search.py     # Neo4j-based code retrieval
│   │   └── vector_search.py    # ChromaDB-based semantic search
│   ├── ui/
│   │   └── app.py              # Streamlit UI implementation
│   ├── ingest.py               # Code ingestion pipeline
│   └── rag_chatbot.py          # Main RAG implementation with FastAPI
├── db/                         # Vector database for storing embeddings
├── .debug/                     # Log files directory
├── environment.yml             # Conda environment configuration
├── requirements.txt            # Pip dependencies
└── .gitignore                  # Git ignore file
```

---

## Technical Details
- **Hybrid Retrieval**: Combines graph traversal (Neo4j) with dense vector search (ChromaDB).
- **Hypothetical Document Embedding (HyDE)**: Uses LLMs to generate Cypher queries from natural language.
- **AST Processing**: Leverages Tree-sitter to extract structured information from C# code.
- **Self-Refining Queries**: The system can refine Neo4j queries based on initial results.
- **Enhanced Vector Retrieval**: Performs metadata filtering and query enhancement for more precise results.
- **LLM Integration**: Uses Ollama API to access models like Mistral for general queries and Codestral for code-specific tasks.

---

## Notes
- The chatbot performs best on C# codebases, as the AST parser is specifically designed for C#.
- Debugging logs are stored in the `.debug` directory for troubleshooting.
- Both Neo4j and ChromaDB must be properly configured for the system to work correctly.

---

## Troubleshooting
- **Neo4j Connection Issues**: Ensure Neo4j is running and accessible at the default location with correct credentials.
- **Missing Dependencies**: Ensure the Conda environment is activated and all dependencies are installed.
- **Database Issues**: If the `db` folder is missing or corrupted, re-run `ingest.py` to regenerate it.
- **Ollama Errors**: Verify that Ollama is running and the required models have been pulled.
- **AST Processing Errors**: Ensure Tree-sitter is correctly installed and can process C# files.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.