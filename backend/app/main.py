"""
Main FastAPI application entry point.
Configures CORS, rate limiting, and registers all API routers.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter

from app.core.config import settings
from app.api.auth_router import router as auth_router
from app.api.profile_router import router as profile_router
from app.api.market_router import router as market_router
from app.api.portfolio_router import router as portfolio_router
from app.api.chat_router import router as chat_router
from app.api.holdings_router import router as holdings_router
from app.api.advice_router import router as advice_router
from app.services.scheduler import start_scheduler

logger = logging.getLogger(__name__)

_startup_status = {
    "rag_ready": False,
    "market_snapshot_ready": False,
    "startup_time": None,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: pre-warm models and start scheduler on startup."""
    t0 = time.time()
    logger.info("Starting Nexus AI backend...")

    # Pre-warm RAG / embedding model to avoid cold-start latency on first user query
    try:
        from app.services.rag_service import get_vector_store
        vs = get_vector_store()
        vs.search("inflation portfolio", top_k=1)
        _startup_status["rag_ready"] = True
        logger.info("RAG embedding model pre-warmed successfully.")
    except Exception as e:
        logger.warning(f"RAG pre-warm skipped (non-fatal): {e}")

    # Validate market snapshot exists
    try:
        import os, json
        snapshot_path = os.path.join(os.path.dirname(__file__), "market_snapshot.json")
        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                json.load(f)
            _startup_status["market_snapshot_ready"] = True
            logger.info("Market snapshot validated at startup.")
    except Exception as e:
        logger.warning(f"Market snapshot validation failed (non-fatal): {e}")

    start_scheduler()
    _startup_status["startup_time"] = round(time.time() - t0, 2)
    logger.info(f"Nexus AI ready in {_startup_status['startup_time']}s")

    yield
    # Shutdown — nothing to clean up currently


# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(
    title="Nexus AI — Explainable Financial Intelligence API",
    description="Deterministic, macro-aware, retrieval-grounded portfolio advisory platform.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ─────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(portfolio_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(holdings_router, prefix="/api/v1/holdings")
app.include_router(advice_router, prefix="/api/v1/portfolio")


# ── Health Check (Rich) ───────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Rich health check — exposes subsystem status for frontend System Status Panel."""
    import os
    snapshot_path = os.path.join(os.path.dirname(__file__), "market_snapshot.json")
    snapshot_fresh = False
    snapshot_age_minutes = None

    if os.path.exists(snapshot_path):
        age_seconds = time.time() - os.path.getmtime(snapshot_path)
        snapshot_age_minutes = round(age_seconds / 60, 1)
        snapshot_fresh = age_seconds < 3600  # Fresh if < 60 min

    return {
        "status": "healthy",
        "version": "2.0.0",
        "subsystems": {
            "rag_engine": "operational" if _startup_status["rag_ready"] else "degraded",
            "market_snapshot": "fresh" if snapshot_fresh else "stale",
            "snapshot_age_minutes": snapshot_age_minutes,
            "portfolio_engine": "deterministic",
            "schema_validation": "active",
        },
        "startup_seconds": _startup_status.get("startup_time"),
    }


# ── Global Exception Handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — no silent crashes, always degrade gracefully."""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "degraded": True,
            "message": "The system has encountered an unexpected error and is operating in fallback mode."
        },
    )

