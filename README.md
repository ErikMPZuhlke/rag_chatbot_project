# RAG Chatbot Project

## Overview

This project implements a Retrieval-Augmented Generation (RAG) chatbot designed to assist with querying and understanding a legacy codebase. The chatbot uses modern machine learning techniques to retrieve relevant code snippets and provide context-aware answers to user questions.

### Key Features
- **Code Ingestion**: Processes and indexes the legacy codebase for efficient retrieval.
- **RAG Chatbot**: Combines retrieved code snippets with a language model to answer user queries.
- **FastAPI Integration**: Provides a RESTful API for querying the chatbot.
- **Streamlit UI**: A user-friendly web interface for interacting with the chatbot.

---

## Architecture

### 1. **Code Ingestion**
- **File**: `ingest.py`
- **Purpose**: 
  - Loads the legacy codebase from the `legacy_code` folder.
  - Splits the code into manageable chunks for better retrieval.
  - Stores the processed data in a vector database (ChromaDB) using embeddings from the `sentence-transformers/all-MiniLM-L6-v2` model.

### 2. **RAG Chatbot**
- **File**: `rag_chatbot.py`
- **Purpose**:
  - Retrieves relevant code snippets from the vector database.
  - Constructs a context-aware prompt for the language model.
  - Uses the Ollama LLM to generate responses based on the retrieved context.

### 3. **Streamlit UI**
- **File**: `app.py`
- **Purpose**:
  - Provides a web-based user interface for interacting with the chatbot.
  - Allows users to input questions and view responses in a simple and intuitive format.
  - Communicates with the FastAPI backend to fetch answers.

### 4. **Legacy Code**
- **Folder**: `legacy_code`
- **Purpose**: Contains the legacy codebase, which is indexed and queried by the chatbot. The content is context-dependent and not directly modified by this project.

---

## Runbook

### Prerequisites
1. **Python Environment**:
   - Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/).
   - Create and activate the Conda environment using the provided `environment.yml` file:
     ```bash
     conda env create -f environment.yml
     conda activate rag_chatbot_env
     ```

2. **Legacy Codebase**:
   - Ensure the `legacy_code` folder contains the codebase you want to index and query.

3. **Install Streamlit**:
   - Ensure Streamlit is installed in your environment:
     ```bash
     pip install streamlit
     ```

---

### Steps to Run

#### 1. **Ingest the Legacy Code**
   - Run the `ingest.py` script to process and index the legacy codebase:
     ```bash
     python ingest.py
     ```
   - This will load the code, split it into chunks, and store the embeddings in a local ChromaDB instance under the `db` folder.

#### 2. **Start the Chatbot API**
   - Run the `rag_chatbot.py` script to start the FastAPI server:
     ```bash
     uvicorn rag_chatbot:app --reload
     ```
   - The API will be available at `http://127.0.0.1:8000`.

#### 3. **Launch the Streamlit UI**
   - Run the `app.py` script to start the Streamlit-based user interface:
     ```bash
     streamlit run app.py
     ```
   - The Streamlit app will open in your default web browser. You can input questions about the legacy codebase and view the chatbot's responses.

---

## Folder Structure

```
rag_chatbot_project/
├── app.py                  # Streamlit-based user interface for the chatbot
├── ingest.py               # Script for processing and indexing the legacy codebase
├── rag_chatbot.py          # FastAPI-based RAG chatbot implementation
├── environment.yml         # Conda environment configuration
├── db/                     # Vector database for storing embeddings
├── legacy_code/            # Folder containing the legacy codebase
└── .vscode/                # VS Code-specific settings
```

---

## Notes
- The chatbot relies on the `sentence-transformers/all-MiniLM-L6-v2` model for embeddings and the Ollama LLM for generating responses.
- The `legacy_code` folder is treated as a black box; its content is indexed but not modified by this project.
- Ensure that the `db` folder is not deleted after ingestion, as it contains the indexed data required for querying.

---

## Troubleshooting
- **Missing Dependencies**: Ensure the Conda environment is activated and all dependencies are installed.
- **Database Issues**: If the `db` folder is missing or corrupted, re-run `ingest.py` to regenerate it.
- **API Errors**: Check the logs for detailed error messages and ensure the FastAPI server is running.
- **Streamlit Issues**: If the Streamlit app doesn't launch, ensure Streamlit is installed and the FastAPI server is running.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.