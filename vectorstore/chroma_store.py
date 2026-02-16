import os

try:
    import chromadb
    from chromadb.utils import embedding_functions

    # Create persistent client (saves locally)
    # Use a specific directory for persistence
    PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

    # Use default embedding function
    embedding_function = embedding_functions.DefaultEmbeddingFunction()

    # Create or get collection
    collection = client.get_or_create_collection(
        name="sar_regulations",
        embedding_function=embedding_function
    )
except Exception as e:
    print(f"Warning: Failed to initialize ChromaDB: {e}. Using mock implementation.")
    
    class MockCollection:
        def __init__(self):
            self.docs = []
            
        def add(self, documents, ids, metadatas=None):
            for i, doc in enumerate(documents):
                self.docs.append({"id": ids[i], "text": doc, "metadata": metadatas[i] if metadatas else {}})
                
        def query(self, query_texts, n_results=2):
            # Simple keyword search mock
            results = []
            for q in query_texts:
                matches = [doc["text"] for doc in self.docs if q.lower() in doc["text"].lower()]
                if not matches:
                    matches = [doc["text"] for doc in self.docs] # Fallback to all if no match
                results.append(matches[:n_results])
            return {"documents": results}
            
        def count(self):
            return len(self.docs)

    collection = MockCollection()
    
    # Mock embedding function type for compatibility if checked elsewhere
    class MockEmbedding:
        pass
    embedding_function = MockEmbedding()

def add_regulation_document(doc_id, text, metadata=None):
    """
    Adds regulatory document to vector store
    """
    if metadata is None:
        metadata = {}
        
    collection.add(
        documents=[text],
        ids=[str(doc_id)],
        metadatas=[metadata]
    )

def retrieve_relevant_docs(query, n_results=2):
    """
    Retrieves relevant regulatory documents
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results["documents"]

def seed_regulatory_knowledge_base():
    """
    Seeds the vector store with initial regulatory documents if empty.
    """
    if collection.count() == 0:
        regulations = [
            {
                "id": "bsa_structuring",
                "text": "Structuring involves breaking down cash transactions into smaller sums to avoid reporting thresholds ($10,000). Patterns of deposits just below this limit are strong indicators. Reference: 31 CFR § 1010.100(xx).",
                "source": "FFIEC BSA/AML Manual"
            },
            {
                "id": "bsa_layering",
                "text": "Layering is the process of separating criminal proceeds from their source by creating a complex web of financial transactions to disguise the audit trail and provide anonymity.",
                "source": "FinCEN Guidance"
            },
            {
                "id": "sar_filing_deadline",
                "text": "A Suspicious Activity Report (SAR) must be filed with FinCEN within 30 days of initial detection of the suspicious activity. If no suspect is identified, the period is extended to 60 days.",
                "source": "31 CFR § 1020.320"
            }
        ]
        
        for reg in regulations:
            add_regulation_document(reg["id"], reg["text"], {"source": reg["source"]})
        print("Knowledge Base Seeded.")
