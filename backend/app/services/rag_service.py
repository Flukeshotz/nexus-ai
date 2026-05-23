"""
Vector Database & RAG Pipeline.
FAISS-based local vector store for financial document retrieval.

Implementation Plan §4.1
Edge Cases:
  - §4.3: Context window overflow → strict token budgeting
"""

import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Token Counter (edgeCases.md §4.3)
# ═══════════════════════════════════════════════════════════════

MAX_CONTEXT_TOKENS = 6000  # Conservative limit for prompt + context
CHARS_PER_TOKEN = 4  # Approximate: 1 token ≈ 4 chars for English text


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length (tiktoken fallback)."""
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def enforce_token_budget(
    chunks: list,
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> list:
    """
    Edge Case §4.3: Trim retrieved chunks to fit within token budget.
    Prevents context window overflow by strict token counting.

    Args:
        chunks: List of text chunks to include in context.
        max_tokens: Maximum allowed tokens for context.

    Returns:
        Trimmed list of chunks that fit within the budget.
    """
    if not chunks:
        return []

    selected = []
    running_tokens = 0

    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk)
        if running_tokens + chunk_tokens <= max_tokens:
            selected.append(chunk)
            running_tokens += chunk_tokens
        else:
            # Truncate last chunk to fit
            remaining = max_tokens - running_tokens
            if remaining > 50:  # Only include if meaningful
                truncated = chunk[:remaining * CHARS_PER_TOKEN]
                selected.append(truncated + "...")
            break

    logger.info(f"Token budget: {running_tokens}/{max_tokens} tokens, {len(selected)}/{len(chunks)} chunks.")
    return selected


# ═══════════════════════════════════════════════════════════════
# FAISS Vector Store
# ═══════════════════════════════════════════════════════════════

class FAISSVectorStore:
    """
    Local FAISS-based vector store for RAG retrieval.
    Uses sentence-transformers for semantic embeddings and faiss-cpu for fast nearest-neighbor search.
    """

    def __init__(self):
        self.documents = []       # List of {"id", "text", "metadata"}
        self.index = None         # faiss index
        self._embedding_dim = 384  # Default for MiniLM
        self._model = None        # Lazy-loaded sentence transformer

    def _get_model(self):
        if self._model is None:
            logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def add_documents(self, texts: list, metadatas: Optional[list] = None) -> int:
        """
        Add documents to the vector store.

        Args:
            texts: List of text chunks.
            metadatas: Optional list of metadata dicts per chunk.

        Returns:
            Number of documents added.
        """
        if not texts:
            return 0

        import faiss

        if metadatas is None:
            metadatas = [{}] * len(texts)

        model = self._get_model()
        new_embeddings = model.encode(texts, convert_to_numpy=True)

        if self.index is None:
            # Using L2 distance
            self.index = faiss.IndexFlatL2(self._embedding_dim)

        self.index.add(new_embeddings)

        for text, metadata in zip(texts, metadatas):
            doc_id = hashlib.md5(text.encode()).hexdigest()
            self.documents.append({
                "id": doc_id,
                "text": text,
                "metadata": metadata,
            })

        logger.info(f"Added {len(texts)} documents. Total: {len(self.documents)}")
        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[dict] = None,
    ) -> list:
        """
        Retrieve top-K most relevant documents for a query.

        Args:
            query: The search query.
            top_k: Number of results to return.
            metadata_filter: Optional {key: value} filter on metadata.

        Returns:
            List of {"text", "metadata", "score"} dicts.
        """
        if not self.documents or self.index is None:
            return []

        model = self._get_model()
        query_vec = model.encode([query], convert_to_numpy=True)

        # Retrieve more if filtering is requested
        search_k = top_k * 5 if metadata_filter else top_k
        distances, indices = self.index.search(query_vec, min(search_k, len(self.documents)))

        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                break
                
            doc = self.documents[idx]
            
            # Apply metadata filter
            if metadata_filter:
                match = True
                for key, value in metadata_filter.items():
                    if doc["metadata"].get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # Convert L2 distance to a similarity score (1 / (1 + distance))
            # so that higher score = more similar, for backward compatibility
            score = 1.0 / (1.0 + float(distances[0][i]))

            results.append({
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": round(score, 4),
            })
            
            if len(results) == top_k:
                break

        return results

    @property
    def document_count(self) -> int:
        return len(self.documents)


# ═══════════════════════════════════════════════════════════════
# RAG Pipeline
# ═══════════════════════════════════════════════════════════════

# Global vector store instance
_vector_store = FAISSVectorStore()


def get_vector_store() -> FAISSVectorStore:
    """Get the global vector store instance."""
    return _vector_store


def rag_retrieve(
    query: str,
    top_k: int = 5,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
    metadata_filter: Optional[dict] = None,
) -> dict:
    """
    RAG retrieval pipeline: search → token budget → return context.

    Returns:
        {
            "context": str (concatenated relevant text),
            "chunks": list of result dicts,
            "total_tokens_estimated": int,
            "truncated": bool,
        }
    """
    store = get_vector_store()
    results = store.search(query, top_k=top_k, metadata_filter=metadata_filter)

    if not results:
        return {
            "context": "",
            "chunks": [],
            "total_tokens_estimated": 0,
            "truncated": False,
        }

    # Extract text chunks
    raw_chunks = [r["text"] for r in results]
    total_raw_tokens = sum(estimate_tokens(c) for c in raw_chunks)

    # Enforce token budget (§4.3)
    trimmed_chunks = enforce_token_budget(raw_chunks, max_tokens=max_context_tokens)
    trimmed_tokens = sum(estimate_tokens(c) for c in trimmed_chunks)

    context = "\n\n---\n\n".join(trimmed_chunks)

    return {
        "context": context,
        "chunks": results[:len(trimmed_chunks)],
        "total_tokens_estimated": trimmed_tokens,
        "truncated": len(trimmed_chunks) < len(raw_chunks),
    }
