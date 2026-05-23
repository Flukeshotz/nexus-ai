# Nexus AI: Architecture Diagrams

These Mermaid diagrams illustrate the core Trust Engineering and Explainability loops in Nexus AI. They are designed for rendering on GitHub or embedding into presentation decks.

## 1. Deterministic Finance Layer vs. Probabilistic LLM
*This diagram shows how we prevented LLM hallucinations by calculating math in Python before querying the AI.*

```mermaid
graph TD
    subgraph Deterministic Core [Python / SQLAlchemy]
        A[User Holdings] --> B(Calculate Net Worth & P&L)
        A --> C(Compare vs Target Risk Profile)
        C --> D{Is Drift > 5%?}
    end

    subgraph Probabilistic Analysis [Groq / Llama-3]
        D -->|Yes| E[Assemble Prompt Context]
        E --> F[LLM: Generate 'Why' & Strategy]
        F --> G[Enforce JSON Schema Response]
    end

    G --> H[Render Smart Alert in UI]

    style A fill:#0f1512,stroke:#61dbb4,stroke-width:2px,color:#fff
    style B fill:#0f1512,stroke:#61dbb4,stroke-width:2px,color:#fff
    style F fill:#2c322e,stroke:#12a480,stroke-width:2px,color:#fff
```

## 2. Market Snapshot Flow (Resilience Architecture)
*This demonstrates the "Cache-First" architecture that prevents live API timeouts from breaking the UI.*

```mermaid
sequenceDiagram
    participant Cron as APScheduler (Backend)
    participant External as yfinance / FRED
    participant DB as SQLite Cache
    participant UI as Client Dashboard

    Cron->>External: Fetch Live Market Data (Hourly)
    alt API Success
        External-->>Cron: Return JSON
        Cron->>DB: Overwrite market_snapshot.json
    else API Timeout / Rate Limit
        External--xCron: Error 503 / 429
        Cron->>DB: Log Error, Retain Previous Snapshot
    end

    UI->>DB: GET /api/v1/market/snapshot
    DB-->>UI: Instantly Return Cached Data
    Note over UI,DB: UI degrades gracefully if timestamp is stale (Confidence drops)
```

## 3. Explainability System & Confidence Calibration
*How the system mathematically assigns "Confidence Scores" to LLM outputs.*

```mermaid
graph LR
    A[Market Data Freshness] --> C(Confidence Calibration Engine)
    B[Semantic Retrieval Quality] --> C
    
    C -->|Fresh Data + High Match| D(Confidence: 95% - High)
    C -->|Stale Data + Good Match| E(Confidence: 75% - Moderate)
    C -->|Missing Data / Conflicting Signals| F(Confidence: <50% - Low/Warn)
    
    D --> G[Frontend Trace Modal]
    E --> G
    F --> G
    
    style C fill:#1b211e,stroke:#86948d,stroke-width:2px,color:#fff
    style D fill:#0f1512,stroke:#10A37F,stroke-width:2px,color:#fff
    style E fill:#0f1512,stroke:#F59E0B,stroke-width:2px,color:#fff
    style F fill:#0f1512,stroke:#EF4444,stroke-width:2px,color:#fff
```

## 4. Scenario Simulator Architecture
*How we process hypotheticals deterministically.*

```mermaid
graph TD
    A[User Selects 'Market Crash -20%'] --> B(Backend: Classify Assets)
    B --> C(Apply -20% to Equity Holdings Only)
    C --> D(Calculate New Total Net Worth)
    D --> E(LLM: Synthesize Impact)
    E --> F[Return 'Impact %' and 'AI Analysis']
    
    style A fill:#252b28,stroke:#dee4df,stroke-width:1px,color:#fff
    style C fill:#0f1512,stroke:#61dbb4,stroke-width:2px,color:#fff
    style E fill:#2c322e,stroke:#12a480,stroke-width:2px,color:#fff
```
