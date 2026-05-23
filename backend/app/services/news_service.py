"""
News & Unstructured Data Fetcher Service.
Fetches financial news from free RSS feeds.
Processes text for the RAG pipeline (cleaning, chunking).
"""

import re
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# RSS Feed Sources
# ═══════════════════════════════════════════════════════════════

RSS_FEEDS = {
    "google_finance": "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "cnbc": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
    "reuters_business": "https://www.reutersagency.com/feed/?best-topics=business-finance",
}


# ═══════════════════════════════════════════════════════════════
# Text Cleaning
# ═══════════════════════════════════════════════════════════════

def clean_text(raw_html: str) -> str:
    """Remove HTML tags, normalize whitespace, and clean text for processing."""
    if not raw_html:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', raw_html)
    # Remove excessive whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Remove special unicode characters
    clean = clean.encode('ascii', 'ignore').decode('ascii')
    return clean


# ═══════════════════════════════════════════════════════════════
# Text Chunking for RAG Embeddings
# ═══════════════════════════════════════════════════════════════

def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
) -> list:
    """
    Split text into overlapping chunks for embedding generation.

    Args:
        text: The full text to chunk.
        chunk_size: Target characters per chunk (approximating ~512 tokens).
        overlap: Number of overlapping characters between chunks.

    Returns:
        List of text chunks.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            boundary = text.rfind('.', start + chunk_size // 2, end)
            if boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


# ═══════════════════════════════════════════════════════════════
# Ticker Extraction
# ═══════════════════════════════════════════════════════════════

COMMON_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
    "JPM", "BAC", "GS", "V", "MA", "JNJ", "PFE", "UNH",
    "SPY", "QQQ", "VTI", "GLD", "TLT", "BTC", "ETH",
}


def extract_tickers(text: str) -> list:
    """Extract potential stock tickers mentioned in text."""
    if not text:
        return []
    # Find all-caps words that are 1-5 characters (typical ticker format)
    potential = re.findall(r'\b([A-Z]{1,5})\b', text)
    # Filter against known tickers to reduce false positives
    found = [t for t in potential if t in COMMON_TICKERS]
    return list(set(found))


# ═══════════════════════════════════════════════════════════════
# RSS Parser
# ═══════════════════════════════════════════════════════════════

def parse_rss_feed(xml_content: str, source_name: str) -> list:
    """
    Parse RSS XML content into article dicts.

    Returns:
        List of article dicts with keys: title, source, url, published_at, content
    """
    articles = []
    try:
        root = ET.fromstring(xml_content)
        items = root.findall('.//item')

        for item in items:
            title = item.findtext('title', '') or ''
            link = item.findtext('link', '') or ''
            pub_date = item.findtext('pubDate', '') or ''
            description = item.findtext('description', '') or ''

            cleaned_content = clean_text(description)
            tickers = extract_tickers(title + " " + cleaned_content)

            articles.append({
                "title": clean_text(title),
                "source": source_name,
                "url": link,
                "published_at": pub_date,
                "content": cleaned_content,
                "tickers_mentioned": tickers,
            })

    except ET.ParseError as e:
        logger.error(f"Failed to parse RSS from {source_name}: {e}")

    return articles


# ═══════════════════════════════════════════════════════════════
# Fetch News (using httpx)
# ═══════════════════════════════════════════════════════════════

async def fetch_news_from_feeds() -> dict:
    """
    Fetch financial news from all configured RSS feeds.

    Returns:
        {
            "articles": list of article dicts,
            "total": int,
            "sources_fetched": list,
            "errors": list,
        }
    """
    try:
        import httpx
    except ImportError:
        return {
            "articles": [],
            "total": 0,
            "sources_fetched": [],
            "errors": ["httpx package not installed."],
        }

    all_articles = []
    sources_fetched = []
    errors = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for source_name, url in RSS_FEEDS.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    articles = parse_rss_feed(response.text, source_name)
                    all_articles.extend(articles)
                    sources_fetched.append(source_name)
                    logger.info(f"Fetched {len(articles)} articles from {source_name}")
                else:
                    errors.append(f"{source_name}: HTTP {response.status_code}")
            except Exception as e:
                errors.append(f"{source_name}: {str(e)}")
                logger.warning(f"Failed to fetch from {source_name}: {e}")

    return {
        "articles": all_articles,
        "total": len(all_articles),
        "sources_fetched": sources_fetched,
        "errors": errors,
    }
