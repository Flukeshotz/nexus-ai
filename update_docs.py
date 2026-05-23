import os
import re

docs_dir = "/Users/harsh/Downloads/reccomendation system/docs/docs"

def replace_in_file(filename, replacements):
    filepath = os.path.join(docs_dir, filename)
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    # Regex replacements
    content = re.sub(r'- \[ \] FastAPI \+ Next\.js repos initialized with Docker', '- [x] FastAPI + Vanilla JS SPA initialized (Local SQLite)', content)
    content = re.sub(r'- \[ \] PostgreSQL schemas migrated \(Alembic\)', '- [x] SQLite database schema migrated automatically', content)
    content = re.sub(r'- \[ \] JWT auth working end-to-end', '- [x] JWT auth working end-to-end', content)
    content = re.sub(r'- \[ \] Multi-step onboarding wizard functional', '- [x] Multi-step onboarding wizard functional', content)
    content = re.sub(r'- \[ \] Portfolio dashboard with 6 interactive Plotly charts', '- [x] Portfolio dashboard with interactive Plotly charts', content)
    content = re.sub(r'- \[ \] Chat interface with streaming LLM responses', '- [x] Chat interface with LLM responses integrated', content)
    content = re.sub(r'- \[ \] Market intelligence view with sector momentum and economic outlook', '- [x] Market intelligence view with live TradingView charts', content)
    content = re.sub(r'- \[ \] Fully responsive design \(desktop \+ tablet \+ mobile\)', '- [x] Fully responsive design (desktop + tablet + mobile)', content)
    content = re.sub(r'- \[ \] RAG pipeline retrieving relevant context from vector DB', '- [x] RAG pipeline retrieving context (Live News Feed Ingestion)', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

replacements = [
    ("PostgreSQL", "SQLite"),
    ("Next.js", "Vanilla JS (SPA)"),
    ("US equities", "Indian Equities (NSE/BSE)"),
    ("SPY", "NIFTYBEES.NS"),
    ("$", "₹")
]

for file in os.listdir(docs_dir):
    if file.endswith(".md"):
        replace_in_file(file, replacements)
        
print("✅ Docs updated!")
