import requests
import json

# Data to feed into the AI's "Brain" (Vector Database)
knowledge_base = [
    {
        "text": "The US Federal Reserve recently announced they will hold interest rates steady at 5.25%-5.50%. This is generally considered bullish for large-cap technology stocks and neutral for bonds.",
        "metadata": {"source": "Fed Minutes", "topic": "Macroeconomics", "date": "2024-05-01"}
    },
    {
        "text": "Inflation (CPI) has cooled slightly to 3.4% year-over-year. Core inflation remains sticky at 3.6%.",
        "metadata": {"source": "BLS Report", "topic": "Inflation", "date": "2024-05-15"}
    },
    {
        "text": "The S&P 500 (SPY) historically returns about 10% annually before inflation. It is a market-cap weighted index of the 500 largest US publicly traded companies.",
        "metadata": {"source": "Market Primer", "topic": "Equities"}
    },
    {
        "text": "Treasury Bonds (TLT) are inversely correlated to interest rates. If the Fed cuts rates, the value of long-term treasury bonds will increase.",
        "metadata": {"source": "Market Primer", "topic": "Fixed Income"}
    },
    {
        "text": "A 'Wash Sale' occurs when an investor sells a security at a loss and buys the same or a substantially identical security within 30 days before or after the sale. The IRS disallows the tax deduction for the loss.",
        "metadata": {"source": "IRS Rules", "topic": "Tax Strategy"}
    }
]

print("🧠 Feeding Knowledge to Nexus AI Vector Database...")

# Extract texts and metadatas into separate lists
texts = [item["text"] for item in knowledge_base]
metadatas = [item["metadata"] for item in knowledge_base]

url = "http://localhost:8000/api/v1/chat/rag/ingest"
payload = {
    "texts": texts,
    "metadatas": metadatas
}

try:
    # 1. Register a dummy admin user
    auth_url = "http://localhost:8000/api/v1/auth"
    requests.post(f"{auth_url}/register", json={
        "email": "admin@nexus.ai",
        "password": "adminpassword123",
        "full_name": "Nexus Admin"
    })
    
    # 2. Login to get token
    login_data = {"username": "admin@nexus.ai", "password": "adminpassword123"}
    token_resp = requests.post(f"{auth_url}/login", data=login_data)
    token = token_resp.json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Send to the backend
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Ingested {data['documents_added']} new documents.")
        print(f"📚 The AI Brain now holds a total of {data['total_documents']} documents.")
        print("\nYou can now ask the AI in the dashboard questions like:")
        print("- 'What did the Fed do recently?'")
        print("- 'How does a Wash Sale work?'")
    else:
        print(f"❌ Failed. Server returned status {response.status_code}: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Ensure your Nexus backend server is running on http://localhost:8000")
