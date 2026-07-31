import os
import chromadb
from chromadb.utils import embedding_functions
from database import get_schema_definitions

# Initialize ChromaDB persistent client
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "schema_index")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH, settings=chromadb.Settings(anonymized_telemetry=False))

# Use sentence-transformers embedding function
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

COLLECTION_NAME = "database_schema"

def get_collection():
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=sentence_transformer_ef
    )

def index_schema():
    """Fetches schema from Postgres and indexes it into ChromaDB."""
    schema_docs = get_schema_definitions()
    if not schema_docs:
        print("No schema found to index.")
        return {"status": "error", "message": "No schema retrieved from DB."}
        
    collection = get_collection()
    
    # We can delete existing to re-index, or upsert. Let's delete and recreate for simplicity
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        collection = get_collection()
    except Exception:
        pass
    
    ids = []
    documents = []
    metadatas = []
    
    for doc in schema_docs:
        ids.append(doc["table"])
        documents.append(doc["description"])
        metadatas.append({"table": doc["table"]})
        
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    return {"status": "success", "tables_indexed": len(schema_docs)}

def retrieve_context(query: str, top_k: int = 5):
    """Retrieves top_k relevant tables for a given user query."""
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    if not results or not results['documents']:
        return []
    
    return results['documents'][0]
