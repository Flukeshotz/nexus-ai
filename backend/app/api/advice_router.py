import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.investor_profile import InvestorProfile
from app.models.portfolio import AIAdviceHistory
from app.api.holdings_router import get_vault_dashboard
from groq import Groq
import os
from app.core.rate_limit import limiter

router = APIRouter(prefix="/advice", tags=["AI Advice"])
logger = logging.getLogger(__name__)

groq_client = None
if hasattr(settings, "GROQ_API_KEY") and settings.GROQ_API_KEY:
    groq_client = Groq(api_key=settings.GROQ_API_KEY)

ADVICE_SYSTEM_PROMPT = """You are Nexus AI, a fiduciary portfolio advisor.
Your goal is to provide hyper-personalized, context-aware analysis of a user's ACTUAL portfolio holdings.

CRITICAL RULES:
1. DO NOT CALCULATE METRICS. Use the pre-computed metrics provided in the context exactly as they are.
2. Provide specific, actionable insights based on the user's risk profile and the current market regime.
3. NEVER hallucinate tickers or assets that the user does not own.
4. PROBABILISTIC LANGUAGE ONLY. Do not use words like "guaranteed", "will rise", "must", or "certain". Frame insights as "Historically aligns with", "May offer", or "Creates an opportunity".
5. Output strictly in JSON format matching the requested schema.
"""

def load_market_snapshot() -> dict:
    try:
        snapshot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_snapshot.json")
        with open(snapshot_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading market snapshot: {e}")
        return {"market_regime": "Unknown", "inflation_trend": "Unknown"}

def calculate_health_score(dashboard: dict, profile: InvestorProfile) -> int:
    """Deterministically calculate health score (0-100)"""
    score = 100
    
    # 1. Diversification penalty (if > 40% in one asset class)
    asset_class_weights = {}
    total_val = dashboard.net_worth
    if total_val == 0:
        return 0
        
    for h in dashboard.holdings:
        asset_class_weights[h.asset_class] = asset_class_weights.get(h.asset_class, 0) + h.current_value
        
    for ac, val in asset_class_weights.items():
        weight = val / total_val
        if weight > 0.4 and ac != "EQUITY": # example simplistic rule
            score -= 10
            
    # 2. Risk penalty
    # If conservative but holds high volatility assets (too complex to calculate here, simplify)
    # 3. P&L Penalty
    if dashboard.total_unrealised_pnl_pct < -5:
        score -= 15
    elif dashboard.total_unrealised_pnl_pct < 0:
        score -= 5
        
    return max(0, min(100, int(score)))

@router.get("/", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def get_portfolio_advice(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not groq_client:
        raise HTTPException(status_code=503, detail="AI Service unavailable.")
        
    # 1. Fetch Profile
    stmt = select(InvestorProfile).where(InvestorProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=400, detail="Investor profile required for AI advice.")
        
    # 2. Fetch Vault Dashboard
    vault = await get_vault_dashboard(db, current_user)
    if vault.net_worth == 0 or not vault.holdings:
        return {
            "health_score": 0,
            "concentration_warning": None,
            "actionable_advice": [],
            "market_context": "Add holdings to receive AI advice."
        }
        
    # 3. Fetch Market Snapshot
    market_snapshot = load_market_snapshot()
    
    # 4. Calculate deterministic health score
    health_score = calculate_health_score(vault, profile)
    
    # 5. Assemble Context
    holdings_summary = []
    asset_classes = {}
    for h in vault.holdings:
        weight = (h.current_value / vault.net_worth) * 100
        asset_classes[h.asset_class] = asset_classes.get(h.asset_class, 0) + weight
        holdings_summary.append(f"- {h.asset_ticker} ({h.asset_class}): {weight:.1f}% weight, P&L: {h.unrealised_pnl_pct:.1f}%")
        
    context = f"""
    --- USER PROFILE ---
    Risk Appetite: {profile.risk_appetite}
    Investment Horizon: {profile.investment_horizon}
    Goals: {', '.join(profile.financial_goals)}
    
    --- PORTFOLIO VAULT ---
    Total Net Worth: {vault.net_worth}
    Total Unrealised P&L: {vault.total_unrealised_pnl_pct:.2f}%
    Asset Allocation: {json.dumps(asset_classes)}
    Holdings:
    {chr(10).join(holdings_summary)}
    
    --- MARKET SNAPSHOT ---
    Regime: {market_snapshot.get('market_regime', 'Neutral')}
    Inflation: {market_snapshot.get('inflation_trend', 'Stable')}
    """
    
    # 6. Deduplication: Fetch recent advice to prevent repeating
    hist_stmt = select(AIAdviceHistory).where(AIAdviceHistory.user_id == current_user.id).order_by(AIAdviceHistory.created_at.desc()).limit(3)
    hist_result = await db.execute(hist_stmt)
    recent_advice = hist_result.scalars().all()
    if recent_advice:
        recent_titles = [h.title for h in recent_advice]
        context += f"\n\n--- RECENT ADVICE (DO NOT REPEAT) ---\n" + "\n".join(recent_titles) + "\nIf a condition persists, escalate urgency or find a new angle instead of repeating verbatim."
    
    
    json_instruction = """
    You must return a JSON object exactly matching this schema:
    {
      "health_score_analysis": "String explaining the deterministic health score based on the context",
      "concentration_warning": "String warning if any asset class is too concentrated, or null",
      "actionable_advice": [
        {
          "title": "Short title of advice (e.g. 'Reduce Tech Exposure')",
          "rationale": "Detailed AI reasoning specifically referencing the user's holdings and P&L. Use probabilistic language.",
          "type": "RISK" | "OPPORTUNITY" | "REBALANCE",
          "confidence_score": Integer between 1 and 100 representing the strength of the market signal
        }
      ],
      "market_context": "One paragraph explaining how the current market regime affects their specific holdings."
    }
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model=settings.GROQ_MODEL_REASONING,
            messages=[
                {"role": "system", "content": ADVICE_SYSTEM_PROMPT + json_instruction},
                {"role": "user", "content": context}
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        
        advice_data = json.loads(completion.choices[0].message.content)
        advice_data["health_score"] = health_score # Override with deterministic score
        
        # Save to History
        for action in advice_data.get("actionable_advice", []):
            history_record = AIAdviceHistory(
                user_id=current_user.id,
                title=action.get("title", "Insight"),
                rationale=action.get("rationale", ""),
                advice_type=action.get("type", "OPPORTUNITY"),
                confidence_score=action.get("confidence_score", 50)
            )
            db.add(history_record)
        
        await db.commit()
        
        return advice_data
        
    except Exception as e:
        logger.error(f"Failed to generate AI advice: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI advice.")

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_advice_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch user's AI advice history."""
    stmt = select(AIAdviceHistory).where(AIAdviceHistory.user_id == current_user.id).order_by(AIAdviceHistory.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    return [
        {
            "id": str(h.id),
            "title": h.title,
            "rationale": h.rationale,
            "type": h.advice_type,
            "confidence_score": h.confidence_score,
            "status": h.status,
            "created_at": h.created_at.isoformat()
        } for h in history
    ]

@router.get("/digest", response_model=Dict[str, Any])
async def get_daily_digest(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch personalized daily morning briefing."""
    if not groq_client:
        return {"bullets": ["AI Service unavailable. Market data cannot be digested."]}
        
    vault = await get_vault_dashboard(db, current_user)
    market_snapshot = load_market_snapshot()
    
    asset_classes = list(set([h.asset_class for h in vault.holdings])) if vault.holdings else []
    
    context = f"""
    --- USER PORTFOLIO ---
    Net Worth: {vault.net_worth}
    Exposure: {', '.join(asset_classes) if asset_classes else 'Cash'}
    
    --- MARKET SNAPSHOT ---
    Regime: {market_snapshot.get('market_regime', 'Neutral')}
    Inflation: {market_snapshot.get('inflation_trend', 'Stable')}
    """
    
    json_instruction = """
    Return exactly this JSON format:
    {
        "greeting": "Short personalized greeting.",
        "market_summary": "One sentence summary of the broader market.",
        "bullets": [
            "Actionable bullet point 1 relating to their specific exposure.",
            "Actionable bullet point 2.",
            "Actionable bullet point 3."
        ]
    }
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model=settings.GROQ_MODEL_REASONING,
            messages=[
                {"role": "system", "content": "You are a proactive financial advisor. Generate a morning briefing." + json_instruction},
                {"role": "user", "content": context}
            ],
            temperature=0.3,
            max_tokens=512,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to generate AI digest: {e}")
        return {"bullets": ["Error generating digest."]}

from app.models.portfolio import SmartAlert

@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_smart_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch unread smart alerts."""
    stmt = select(SmartAlert).where(
        SmartAlert.user_id == current_user.id,
        SmartAlert.is_read == False
    ).order_by(SmartAlert.created_at.desc())
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "type": a.alert_type,
            "message": a.message,
            "severity": a.severity,
            "created_at": a.created_at.isoformat()
        } for a in alerts
    ]
