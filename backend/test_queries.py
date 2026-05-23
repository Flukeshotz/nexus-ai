import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.chat_agent import process_chat_message
from app.services.rag_service import get_vector_store

def setup_rag():
    # Let's add some dummy data so the vector store isn't empty, otherwise 
    # the LLM won't have context if it falls back to RAG.
    store = get_vector_store()
    store.add_documents([
        "Gold is a traditional inflation hedge because it maintains purchasing power when fiat currencies devalue. During high inflation, investors flock to gold.",
        "Diversification involves spreading investments across different asset classes to reduce unsystematic risk.",
        "Tech stocks usually suffer during interest rate hikes."
    ])

def run_tests():
    setup_rag()
    
    queries = [
        "What is diversification?",
        "Why is gold useful during inflation?"
    ]
    
    for q in queries:
        print(f"\n{'='*50}\nQuery: {q}\n{'='*50}")
        try:
            result = process_chat_message(q)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    run_tests()
