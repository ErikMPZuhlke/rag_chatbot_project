from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import DirectoryLoader

# Path to your legacy code
CODE_DIR = "./legacy_code"

# Load a free local embedding model
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def ingest_code():
    loader = DirectoryLoader(CODE_DIR, glob="**/*.cs", show_progress=True)
    documents = loader.load()

    # Split by function/class for better chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # ChromaDB store with free embeddings
    vector_db = Chroma.from_documents(docs, embedding_model, persist_directory="./db")
    vector_db.persist()
    print(f"Ingested {len(docs)} chunks into ChromaDB.")

if __name__ == "__main__":
    ingest_code()
