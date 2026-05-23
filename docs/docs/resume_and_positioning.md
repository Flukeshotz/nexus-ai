# Nexus AI: Resume & Positioning Assets

This document contains high-impact copy optimized for applicant tracking systems (ATS), recruiters, and PM interviews. The focus is strictly on PM tradeoffs, operational maturity, and Trust Engineering.

## 1. Resume Bullets
*Use these under your "Projects" or "Experience" section.*

**Option 1: Product Management Focus**
* **Spearheaded** the development of Nexus AI, an explainable financial intelligence platform that combines deterministic portfolio math with retrieval-grounded (RAG) LLM reasoning to proactively monitor asset allocation.
* **Engineered a Trust Framework** separating qualitative AI advisory from quantitative portfolio math, deploying confidence scoring and recommendation deduplication to eliminate LLM hallucinations and robotic repetition.
* **Driven by PM rigor**, prioritized deterministic SQLite storage, Dockerized container orchestration, and Pydantic schema validation to achieve a robust, portable "zero-fail" demo architecture.

**Option 2: Technical/AI Focus**
* **Architected** an anticipatory financial operating system leveraging FastAPI, vanilla JS, and the Groq (Llama-3) API for low-latency market analysis.
* **Implemented** a resilient backend pipeline integrating `APScheduler` for hourly portfolio drift detection and `slowapi` rate-limiting to protect LLM endpoints from quota exhaustion.
* **Mitigated edge cases** like API failures and semantic contamination by instituting a Cache-First Snapshot architecture with graceful UI degradation.

## 2. LinkedIn Launch Copy

**Headline:** 
Just launched Nexus AI: An explainable, macro-aware financial intelligence platform.

**Body:**
The biggest problem in AI finance isn't predicting stock prices—it's the massive "trust gap" created by black-box chatbots that hallucinate advice without context. 

I built Nexus AI to prove that the future of fintech relies on **Trust Engineering**. 

Instead of asking an LLM to guess market conditions, Nexus AI separates the math from the language. Hard financial metrics (Net Worth, P&L, Portfolio Drift) are calculated deterministically in Python. The LLM (Llama-3 via Groq) is strictly confined to translating those mathematical realities into human-readable strategies.

**Key Features:**
🛡️ **Trust Interface:** Every AI recommendation comes with explicit Confidence Scoring.
📉 **Proactive Intelligence:** Replaced reactive chatbots with a Daily AI Digest and Smart Alerts that actively monitor portfolio drift.
🧪 **Scenario Simulator:** A deterministic engine that stress-tests your portfolio against Market Crashes or Tech Rallies, with AI explaining *why* it reacted that way.
🐳 **Production Ready:** Fully Dockerized (FastAPI + Nginx) with rate-limiting and resilient background scheduling.

Check out the full PM Case Study and codebase here: [Link to GitHub]
*(Attach Screenshot of Timeline or Confidence Modal)*

## 3. PM Interview Talking Points

If asked: *"Tell me about a time you had to make a difficult product tradeoff."*
**The Nexus AI Answer:**
> "When building Nexus AI, I had to choose between using a complex LangGraph autonomous agent framework versus a simpler deterministic intent router. I chose the deterministic route. While recursive agents look great on paper, they increase latency, cost, and hallucination risk without adding proportional value to the user. By constraining the AI to *explain* deterministic math rather than *invent* it, I dramatically increased system trust—which was the core KPI of the product."

If asked: *"How do you handle edge cases and failures in AI?"*
**The Nexus AI Answer:**
> "AI models fail constantly. In Nexus AI, I built a Cache-First Snapshot Architecture. Instead of querying live market APIs for every chat prompt—which leads to timeouts and broken UX—a background cron job caches the market state every 15 minutes. If the upstream API goes down, the frontend doesn't break; it gracefully degrades, showing a slightly older timestamp and a visibly lowered AI Confidence Score. I prioritized reliability over real-time perfection."
