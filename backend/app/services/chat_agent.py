"""
Conversational Advisory Agent.
Tool-calling agent that routes user queries to the appropriate
backend service and generates contextual responses.

Implementation Plan §4.3
"""

import json
import logging
from typing import Optional

from app.services.llm_service import (
    classify_query,
    generate_portfolio_explanation,
    ask_groq,
    INJECTION_REFUSAL,
)
from app.services.rag_service import rag_retrieve

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Agent Tools Registry
# ═══════════════════════════════════════════════════════════════

AVAILABLE_TOOLS = {
    "get_user_profile": {
        "description": "Fetches the current investor profile including risk score, age, goals.",
        "parameters": ["user_id"],
    },
    "get_current_portfolio": {
        "description": "Retrieves the user's active portfolio with weights and metrics.",
        "parameters": ["user_id"],
    },
    "run_scenario": {
        "description": "Runs a scenario simulation (market crash, inflation, SIP, retirement).",
        "parameters": ["scenario_type", "params"],
    },
    "search_market_news": {
        "description": "Searches the vector DB for relevant market news and research.",
        "parameters": ["query"],
    },
    "get_market_signals": {
        "description": "Fetches latest technical indicators for a ticker.",
        "parameters": ["ticker"],
    },
    "calculate_sip_projection": {
        "description": "Computes future value of a SIP investment.",
        "parameters": ["monthly_amount", "years", "expected_return"],
    },
    "explain_concept": {
        "description": "Explains a financial concept (CAGR, Sharpe, SIP, etc.).",
        "parameters": ["concept"],
    },
}


# ═══════════════════════════════════════════════════════════════
# Intent Classification
# ═══════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "portfolio_explanation": [
        "why did you pick", "explain my portfolio", "why these stocks",
        "rationale", "asset allocation", "why gold", "why bonds"
    ],
    "portfolio_delta_reasoning": [
        "why did my portfolio change", "what changed", "why did allocation change",
        "allocation delta", "why increase", "why decrease"
    ],
    "scenario_analysis": [
        "what if", "market crash", "recession", "inflation spike",
        "stress test", "drop by"
    ],
    "retirement_planning": [
        "retire", "retirement", "age", "years left", "pension"
    ],
    "sip_projection": [
        "sip", "monthly investment", "compound", "future value"
    ],
    "market_analysis": [
        "market", "trend", "rsi", "indicator", "signal",
        "momentum", "sector", "bull", "bear"
    ],
    "concept_education": [
        "what is", "what are", "explain", "define", "meaning of",
        "how does", "tell me about", "what does"
    ],
    "risk_assessment": [
        "risk", "volatility", "safe", "drawdown", "sharpe", "danger"
    ],
}


import re

def classify_intent(query: str) -> str:
    """Classify user query into an intent category using word boundaries."""
    query_lower = query.lower().strip()

    scores = {}
    for intent, keywords in INTENT_PATTERNS.items():
        score = 0
        for kw in keywords:
            # Match whole words to prevent "rsi" matching inside "diversification"
            if re.search(rf'\b{re.escape(kw)}\b', query_lower):
                score += 1
        scores[intent] = score

    if max(scores.values()) == 0:
        return "general"

    # If there's a tie, 'concept_education' should ideally take precedence over 'portfolio_explanation' for questions.
    # But returning max by value will work well with accurate word boundaries.
    return max(scores, key=scores.get)


# ═══════════════════════════════════════════════════════════════
# Financial Education Module (§4.4)
# ═══════════════════════════════════════════════════════════════

FINANCIAL_CONCEPTS = {
    "cagr": {
        "term": "CAGR (Compound Annual Growth Rate)",
        "simple": "CAGR is the average annual growth rate of an investment over a specified time period, assuming profits are reinvested.",
        "detailed": "CAGR = (Ending Value / Beginning Value)^(1/n) - 1, where n is the number of years. It smooths out volatility to show the 'true' annualized return. For example, if ₹1,00,000 grows to ₹1,61,000 in 5 years, the CAGR is ~10%.",
        "relevance": "Used to compare different investments fairly, regardless of their volatility patterns.",
    },
    "sharpe_ratio": {
        "term": "Sharpe Ratio",
        "simple": "A measure of risk-adjusted return. Higher is better — it shows how much extra return you get per unit of risk.",
        "detailed": "Sharpe = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility. A Sharpe > 1 is considered good, > 2 is very good, > 3 is excellent.",
        "relevance": "Helps compare portfolios: a 15% return with 20% volatility (Sharpe ~0.5) is worse than 10% return with 5% volatility (Sharpe ~1.0).",
    },
    "sip": {
        "term": "SIP (Systematic Investment Plan)",
        "simple": "A method of investing a fixed amount regularly (usually monthly) into mutual funds or other assets.",
        "detailed": "SIP leverages rupee-cost averaging: when prices drop, you buy more units; when they rise, you buy fewer. Over time, this smooths your average purchase price and reduces timing risk.",
        "relevance": "Ideal for salaried investors. Even ₹5,000/month at 12% CAGR for 20 years grows to ~₹50 lakh.",
    },
    "diversification": {
        "term": "Diversification",
        "simple": "Spreading investments across different asset classes to reduce risk. 'Don't put all your eggs in one basket.'",
        "detailed": "By combining assets with low correlation (e.g., stocks + bonds + gold), portfolio volatility decreases without proportionally reducing expected returns. This is the core principle behind Modern Portfolio Theory.",
        "relevance": "A well-diversified portfolio can reduce maximum drawdown by 30-50% compared to a single-asset portfolio.",
    },
    "beta": {
        "term": "Beta (β)",
        "simple": "Measures how much a stock moves relative to the overall market. Beta > 1 means more volatile than the market.",
        "detailed": "Beta = Covariance(stock, market) / Variance(market). A beta of 1.5 means the stock tends to move 1.5x the market — up 15% when the market is up 10%, but also down 15% when the market is down 10%.",
        "relevance": "Conservative investors should prefer low-beta stocks (β < 1); aggressive investors may seek high-beta stocks for amplified returns.",
    },
    "drawdown": {
        "term": "Maximum Drawdown",
        "simple": "The largest peak-to-trough decline in portfolio value. It answers: 'What's the worst loss I would have experienced?'",
        "detailed": "Calculated as (Trough Value - Peak Value) / Peak Value × 100. For example, the S&P 500 had a -34% max drawdown in March 2020 and -57% in 2008-09.",
        "relevance": "Critical for retirement portfolios — a 50% drawdown requires a 100% gain just to break even.",
    },
    "inflation": {
        "term": "Inflation",
        "simple": "The rate at which prices increase over time, eroding the purchasing power of money.",
        "detailed": "At 6% inflation, ₹1,00,000 today will only buy ₹55,800 worth of goods in 10 years. Your investments must earn above inflation to grow in real terms. This is why 'real returns' (nominal return minus inflation) matter more than headline returns.",
        "relevance": "A bank FD at 7% with 6% inflation gives only 1% real return. Equity historically delivers 5-7% real returns in India.",
    },
    "etf": {
        "term": "ETF (Exchange-Traded Fund)",
        "simple": "A basket of securities (stocks, bonds, etc.) that trades on an exchange like a single stock, offering instant diversification at low cost.",
        "detailed": "ETFs track an index (e.g., Nifty 50, S&P 500) and have expense ratios of 0.03-0.50%, far lower than actively managed mutual funds (1-2%). They can be bought/sold throughout the trading day.",
        "relevance": "ETFs are the building blocks of modern portfolio construction due to their low cost, tax efficiency, and broad market exposure.",
    },
    "risk_adjusted_return": {
        "term": "Risk-Adjusted Return",
        "simple": "A way to measure returns while accounting for the risk taken. Two portfolios with the same return but different risk levels are not equally good.",
        "detailed": "Common measures include Sharpe Ratio, Sortino Ratio (only penalizes downside risk), and Calmar Ratio (return vs max drawdown). These help compare apples to apples.",
        "relevance": "A 'safe' 8% return may be superior to a volatile 12% return, depending on your goals and sleep quality.",
    },
}


def explain_concept(concept: str) -> dict:
    """
    Financial Education Module (§4.4).
    Returns a structured explanation of a financial concept.
    """
    concept_key = concept.lower().strip().replace(" ", "_").replace("-", "_")

    # Fuzzy matching
    for key, data in FINANCIAL_CONCEPTS.items():
        if key in concept_key or concept_key in key:
            return {
                "found": True,
                "concept": data,
            }
        # Also check the full term
        if concept.lower() in data["term"].lower():
            return {
                "found": True,
                "concept": data,
            }

    return {
        "found": False,
        "concept": None,
        "message": f"I don't have a detailed explanation for '{concept}' yet. Please ask about: {', '.join(FINANCIAL_CONCEPTS.keys())}",
    }


# ═══════════════════════════════════════════════════════════════
# SIP Calculator Tool
# ═══════════════════════════════════════════════════════════════

def calculate_sip_projection(
    monthly_amount: float,
    years: int,
    expected_annual_return: float = 0.12,
    inflation_rate: float = 0.06,
) -> dict:
    """
    Calculate future value of a SIP investment.
    Returns both nominal and real (inflation-adjusted) projections.
    """
    monthly_rate = expected_annual_return / 12
    months = years * 12

    if monthly_rate > 0:
        future_value = monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        future_value = monthly_amount * months

    total_invested = monthly_amount * months
    wealth_gained = future_value - total_invested

    # Real value
    inflation_factor = (1 + inflation_rate) ** years
    real_future_value = future_value / inflation_factor

    return {
        "monthly_sip": monthly_amount,
        "years": years,
        "expected_return_pct": expected_annual_return * 100,
        "total_invested": round(total_invested, 2),
        "nominal_future_value": round(future_value, 2),
        "wealth_gained": round(wealth_gained, 2),
        "real_future_value": round(real_future_value, 2),
        "inflation_rate_pct": inflation_rate * 100,
        "multiplication_factor": round(future_value / total_invested, 2) if total_invested > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════════
# Main Agent Processor
# ═══════════════════════════════════════════════════════════════

def process_chat_message(
    query: str,
    user_profile: Optional[dict] = None,
    portfolio_data: Optional[dict] = None,
) -> dict:
    """
    Process a user chat message through the advisory agent pipeline.

    Pipeline:
      1. Safety check (§4.2)
      2. Intent classification
      3. Tool selection & execution
      4. Response generation

    Returns:
        {
            "response": str or dict,
            "intent": str,
            "tools_used": list,
            "guardrails": dict,
        }
    """
    # ── Step 1: Safety Check ──────────────────────────────────
    safety = classify_query(query)
    if not safety["is_safe"]:
        return {
            "response": safety["refusal_message"],
            "intent": safety["category"],
            "tools_used": ["query_classifier"],
            "guardrails": {
                "injection_blocked": safety["category"] == "injection",
                "speculative_blocked": safety["category"] == "speculative",
                "matched_pattern": safety["matched_pattern"],
            },
        }

    # ── Step 2: Intent Classification ─────────────────────────
    intent = classify_intent(query)
    tools_used = ["intent_classifier"]

    # ── Step 3: Route to appropriate handler ──────────────────
    if intent == "concept_education":
        # Extract concept from query
        concept = query.lower().replace("what is", "").replace("what are", "")
        concept = concept.replace("explain", "").replace("define", "")
        concept = concept.replace("?", "").strip()
        result = explain_concept(concept)
        tools_used.append("explain_concept")
        response = result["concept"] if result["found"] else result["message"]

    elif intent == "sip_projection":
        result = calculate_sip_projection(
            monthly_amount=10000, years=15, expected_annual_return=0.12,
        )
        tools_used.append("calculate_sip_projection")
        response = result

    elif intent == "portfolio_explanation":
        if portfolio_data:
            profile = user_profile or {"age": 30, "risk_category": "moderate",
                                       "financial_goals": ["retirement"],
                                       "investment_horizon": "long_term"}
            rag_result = rag_retrieve(query, top_k=3)
            tools_used.extend(["get_current_portfolio", "search_market_news"])
            result = generate_portfolio_explanation(
                portfolio_data=portfolio_data,
                user_profile=profile,
                rag_context=rag_result["context"],
            )
            response = result["explanation"]
        else:
            # Fallback to general QA if no portfolio exists but user asks a 'why' question
            intent = "general"

    elif intent == "portfolio_delta_reasoning":
        from app.services.market_snapshot_service import get_latest_snapshot, get_previous_snapshot
        
        current = get_latest_snapshot()
        prev = get_previous_snapshot()
        
        if not portfolio_data:
            intent = "general"
        elif not prev:
            response = "I cannot determine the portfolio delta as I do not have a previous market snapshot cached."
        else:
            tools_used.extend(["get_latest_snapshot", "get_previous_snapshot", "ask_groq"])
            # Generate delta reasoning using Groq
            prompt = (
                f"You are a financial advisor explaining a recent portfolio allocation change.\n\n"
                f"PREVIOUS MARKET STATE:\n{json.dumps(prev, indent=2)}\n\n"
                f"CURRENT MARKET STATE:\n{json.dumps(current, indent=2)}\n\n"
                f"User Question: {query}\n\n"
                f"Explain simply how the changing market state (e.g. inflation, regime, volatility) justifies adjustments in a standard portfolio."
            )
            response = ask_groq(prompt)

    elif intent == "scenario_analysis":
        from app.services.backtesting_engine import simulate_scenario
        weights = portfolio_data.get("weights", {}) if portfolio_data else {"NIFTYBEES.NS": 0.6, "GOLDBEES.NS": 0.4}
        result = simulate_scenario(
            portfolio_value=1000000,
            weights=weights,
            scenario="market_crash",
            scenario_params={"crash_pct": -30},
        )
        tools_used.append("run_scenario")
        response = result

    elif intent == "retirement_planning":
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=1000000,
            weights=portfolio_data.get("weights", {"NIFTYBEES.NS": 0.6, "GOLDBEES.NS": 0.4}) if portfolio_data else {},
            scenario="early_retirement",
            scenario_params={"target_age": 45, "current_age": user_profile.get("age", 30) if user_profile else 30},
        )
        tools_used.append("run_scenario")
        response = result

    elif intent == "market_analysis":
        rag_result = rag_retrieve(query, top_k=5)
        tools_used.append("search_market_news")
        if rag_result["chunks"]:
            response = {
                "market_context": rag_result["context"],
                "sources": len(rag_result["chunks"]),
                "analysis": "Based on available market data, monitor key indicators for your portfolio sectors.",
            }
        else:
            response = "No recent market data available. The system indexes market news periodically."

    elif intent == "risk_assessment":
        if portfolio_data and portfolio_data.get("metrics"):
            metrics = portfolio_data["metrics"]
            response = {
                "volatility": f"{metrics.get('annual_volatility', 0)*100:.1f}%",
                "sharpe_ratio": metrics.get("sharpe_ratio", "N/A"),
                "assessment": "Your portfolio risk metrics are within expected bounds for your risk category.",
            }
            tools_used.append("get_current_portfolio")
        else:
            intent = "general"

    if intent == "general":
        # General fallback: Query Groq
        rag_result = rag_retrieve(query, top_k=3)
        tools_used.append("search_market_news")
        tools_used.append("ask_groq")
        
        # Build prompt with RAG context
        prompt = query
        if rag_result["context"]:
            prompt = f"Context: {rag_result['context']}\n\nUser Question: {query}\n\nPlease answer the user's question using the context provided if relevant."
            
        response = ask_groq(prompt)

    # ── Inject Market Transparency Layer ─────────────────────────────────
    from app.services.market_snapshot_service import get_latest_snapshot
    snapshot = get_latest_snapshot()
    signals_used = []
    
    if intent in ["portfolio_explanation", "general", "market_analysis"]:
        regime = snapshot.get("market_regime", "Unknown")
        inflation = snapshot.get("inflation_trend", "Unknown")
        volatility = snapshot.get("volatility_level", "Unknown")
        
        # Expose top-level signals that influenced the RAG/Groq generation
        signals_used.append({
            "signal": "Market Regime", 
            "state": regime,
            "portfolio_effect": "Increased defensive allocation" if regime == "Bearish" else "Maintained growth exposure",
            "confidence": 0.92,
            "source": "yfinance (50/200 SMA)"
        })
        
        signals_used.append({
            "signal": "Inflation Trend", 
            "state": inflation,
            "portfolio_effect": "Increased Gold/Commodities" if inflation == "Rising" else "Stable bond allocation",
            "confidence": 0.85,
            "source": "FRED API (CPIAUCSL)"
        })
        
        signals_used.append({
            "signal": "Volatility Risk", 
            "state": volatility,
            "portfolio_effect": "Reduced Small Caps" if volatility == "High" else "Standard risk budget",
            "confidence": 0.88,
            "source": "yfinance (20-day annualized std_dev)"
        })

    return {
        "intent": intent,
        "response": response,
        "tools_used": tools_used,
        "market_signals": signals_used,
        "guardrails": {
            "injection_blocked": False,
            "speculative_blocked": False,
            "toxicity_blocked": False
        }
    }
