import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import FAISSVectorStore

def test():
    print("Initializing FAISS Vector Store...")
    store = FAISSVectorStore()
    
    print("Adding documents...")
    store.add_documents(
        ["Apple stock surges on strong iPhone sales and tech growth",
         "Federal Reserve raises interest rates by 25 basis points",
         "Gold prices reach all-time high amid geopolitical tensions"],
        [{"sector": "tech"}, {"sector": "macro"}, {"sector": "commodities"}]
    )
    
    print(f"Total documents: {store.document_count}")
    
    print("Searching for 'Apple stock surges tech'...")
    results = store.search("Apple stock surges tech", top_k=2)
    print(results)

if __name__ == "__main__":
    test()
