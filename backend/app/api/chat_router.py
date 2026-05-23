"""
Chat & AI Advisory API Router.
Endpoints for conversational agent, portfolio explanation,
financial education, and RAG search.

Implementation Plan §4.2, §4.3, §4.4
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["AI Advisory & Chat"])


# ── Request Schemas ───────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request for conversational chat."""
    message: str = Field(..., min_length=1, max_length=2000)
    portfolio_data: Optional[dict] = Field(None, description="Current portfolio weights/metrics")
    user_profile: Optional[dict] = Field(None, description="User profile context")


class ExplainPortfolioRequest(BaseModel):
    """Request for portfolio explanation generation."""
    portfolio_data: dict = Field(...)
    user_profile: dict = Field(...)
    rag_query: Optional[str] = Field(None, description="Optional query for RAG context")


class EducationRequest(BaseModel):
    """Request for financial concept explanation."""
    concept: str = Field(..., min_length=1, max_length=200)


class SIPRequest(BaseModel):
    """Request for SIP projection."""
    monthly_amount: float = Field(..., ge=100)
    years: int = Field(..., ge=1, le=50)
    expected_annual_return: float = Field(0.12, ge=0, le=1.0)
    inflation_rate: float = Field(0.06, ge=0, le=0.5)


class RAGSearchRequest(BaseModel):
    """Request for RAG vector search."""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=20)


class RAGIngestRequest(BaseModel):
    """Request to add documents to vector store."""
    texts: list = Field(...)
    metadatas: Optional[list] = None


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/message")
async def chat_message(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the AI advisory agent.
    Handles: portfolio queries, scenario analysis, market questions,
    financial education, and SIP projections.

    Guardrails: prompt injection detection, speculative query blocking.
    """
    from app.services.chat_agent import process_chat_message

    result = process_chat_message(
        query=data.message,
        user_profile=data.user_profile,
        portfolio_data=data.portfolio_data,
    )

    return result


@router.post("/explain-portfolio")
async def explain_portfolio(
    data: ExplainPortfolioRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a comprehensive, human-readable portfolio explanation.
    Returns structured explanation + LLM-ready prompt.
    """
    from app.services.llm_service import generate_portfolio_explanation
    from app.services.rag_service import rag_retrieve

    rag_context = ""
    if data.rag_query:
        rag_result = rag_retrieve(data.rag_query, top_k=3)
        rag_context = rag_result["context"]

    result = generate_portfolio_explanation(
        portfolio_data=data.portfolio_data,
        user_profile=data.user_profile,
        rag_context=rag_context,
    )

    return result


@router.post("/education")
async def financial_education(
    data: EducationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Explain a financial concept.
    Supports: CAGR, Sharpe Ratio, SIP, Diversification, Beta,
    Drawdown, Inflation, ETF, Risk-Adjusted Returns.
    """
    from app.services.chat_agent import explain_concept

    result = explain_concept(data.concept)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/sip-projection")
async def sip_projection(
    data: SIPRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Calculate SIP future value with inflation adjustment.
    Returns nominal and real projected values.
    """
    from app.services.chat_agent import calculate_sip_projection

    result = calculate_sip_projection(
        monthly_amount=data.monthly_amount,
        years=data.years,
        expected_annual_return=data.expected_annual_return,
        inflation_rate=data.inflation_rate,
    )

    return result


@router.post("/rag/search")
async def rag_search(
    data: RAGSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Search the vector database for relevant financial documents.
    Returns ranked results with relevance scores.
    """
    from app.services.rag_service import rag_retrieve

    result = rag_retrieve(data.query, top_k=data.top_k)
    return result


@router.post("/rag/ingest")
async def rag_ingest(
    data: RAGIngestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Ingest documents into the RAG vector store.
    Processes text chunks and generates embeddings.
    """
    from app.services.rag_service import get_vector_store

    if not data.texts:
        raise HTTPException(status_code=422, detail="No texts provided.")

    store = get_vector_store()
    count = store.add_documents(data.texts, data.metadatas)

    return {
        "documents_added": count,
        "total_documents": store.document_count,
    }


@router.get("/guardrails/check")
async def check_guardrails(
    query: str,
    current_user: User = Depends(get_current_user),
):
    """
    Check if a query passes safety guardrails.
    Tests for prompt injection and speculative content.
    """
    from app.services.llm_service import classify_query

    result = classify_query(query)
    return result
