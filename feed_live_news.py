import requests
import json
import urllib.request
import xml.etree.ElementTree as ET

# 1. Login to get an authentication token
auth_url = "http://localhost:8000/api/v1/auth"

# Try to register first, ignore if already registered
try:
    requests.post(f"{auth_url}/register", json={
        "email": "news_bot@nexus.ai",
        "password": "strongpassword123",
        "full_name": "Nexus News Bot"
    })
except Exception:
    pass

print("🔐 Authenticating...")
# Login using JSON (UserLoginRequest)
login_data = {"email": "news_bot@nexus.ai", "password": "strongpassword123"}
token_resp = requests.post(f"{auth_url}/login", json=login_data)
token = token_resp.json().get("access_token")

if not token:
    print("❌ Failed to get auth token. Is the backend running?")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# 2. Fetch Live Market News from an RSS Feed (e.g. Moneycontrol / Yahoo Finance India)
print("📡 Fetching Live Market News...")
news_feed_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI,RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS&region=IN&lang=en-IN"

try:
    req = urllib.request.Request(news_feed_url, headers={'User-Agent': 'Mozilla/5.0'})
    xml_data = urllib.request.urlopen(req).read()
    root = ET.fromstring(xml_data)
except Exception as e:
    print(f"❌ Failed to fetch RSS: {e}")
    exit(1)

texts = []
metadatas = []

# Parse the RSS feed items
for item in root.findall('./channel/item')[:15]:  # Get top 15 news items
    title = item.find('title').text
    description = item.find('description').text if item.find('description') is not None else ""
    pubDate = item.find('pubDate').text
    
    # Clean up description (remove HTML tags if any)
    import re
    clean_desc = re.sub('<[^<]+>', '', description)
    
    content = f"Title: {title}. Context: {clean_desc}"
    texts.append(content)
    metadatas.append({"source": "Yahoo Finance RSS", "topic": "Live Market News", "date": pubDate})

if not texts:
    print("⚠️ No news articles found.")
    exit(1)

print(f"✅ Found {len(texts)} live articles. Feeding them to Nexus AI Brain...")

# 3. Feed the data to the RAG Database
ingest_url = "http://localhost:8000/api/v1/chat/rag/ingest"
payload = {"texts": texts, "metadatas": metadatas}

response = requests.post(ingest_url, json=payload, headers=headers)
if response.status_code == 200:
    data = response.json()
    print(f"✅ Success! Ingested {data['documents_added']} new articles into the AI.")
    print("\nAsk the AI Advisor right now: 'What is the latest news affecting the Nifty 50 or Reliance?'")
else:
    print(f"❌ Failed. Server returned status {response.status_code}: {response.text}")
