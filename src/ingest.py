from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from py2neo import Graph, Node, Relationship
from code_processing.ast_processing import CSharpASTProcessor

def insert_into_neo4j(graph_data):
    NEO4J_URI = "bolt://localhost:7687"
    graph_db = Graph(NEO4J_URI, auth=("neo4j", "password"))
    tx = graph_db.begin()
    
    for namespace in graph_data['namespaces']:
        namespace_node = Node("Namespace", name=namespace['name'])
        tx.merge(namespace_node, "Namespace", "name")

    for cls in graph_data['classes']:
        class_node = Node("Class", name=cls['name'], filename=cls['filename'], docstring=cls['docstring'])
        tx.merge(class_node, "Class", "name")

        # Create relationship between class and its namespace
        namespace_node = Node("Namespace", name=cls['namespace'])
        tx.merge(namespace_node, "Namespace", "name")
        tx.merge(Relationship(namespace_node, "CONTAINS", class_node))

    for method in graph_data['methods']:
        method_node = Node("Method", name=method['name'], docstring=method['docstring'], code=method['code'])
        tx.merge(method_node, "Method", "name")

        # Create relationship between method and its class
        class_node = Node("Class", name=method['class'])
        tx.merge(class_node, "Class", "name")
        tx.merge(Relationship(class_node, "CONTAINS", method_node))

    tx.commit()

def process_abstract_syntax_tree(file_path):
    builder = CSharpASTProcessor()
    graph_data = builder.process_source_dir(source_dir=file_path)
    insert_into_neo4j(graph_data)

    print("AST successfully stored in Neo4j!")
    return graph_data
                        
def vectorize_code_chunks(graph_data):
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="./db", embedding_function=embedding_model)
    
    # Prepare method code for embedding
    method_documents = []
    for method in graph_data['methods']:
        method_code = method['code']
        # Create proper Document objects instead of dictionaries
        method_documents.append(
            Document(
                page_content=method_code,
                metadata={"method_name": method['name'], "class_name": method['class']}
            )
        )
    
    # Split method code into chunks for better embedding
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    docs = text_splitter.split_documents(method_documents)
    
    # Store method code in ChromaDB
    vector_db = Chroma.from_documents(docs, embedding_model, persist_directory="./db")
    vector_db.persist()

    print(f"Ingested {len(docs)} method code chunks into ChromaDB.")

def ingest_code(directory="./legacy_code"):
    """Scan C# code and insert relationships into Neo4j and ChromaDB."""
    graph_data = process_abstract_syntax_tree(directory)
    vectorize_code_chunks(graph_data)
    
    print("✅ C# code structure stored in Neo4j & ChromaDB!")

if __name__ == "__main__":
    ingest_code()
