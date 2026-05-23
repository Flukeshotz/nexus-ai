/**
 * Explainability Adapter
 * Translates raw backend signals into structured, narrative UI objects.
 */

export function normalizeSignal(backendSignal) {
    // Input format: { signal: "Inflation Trend", state: "Rising", portfolio_effect: "...", confidence: 0.85, source: "FRED" }
    
    // Determine severity/color class based on standard financial semantics
    let severity = "neutral";
    const stateLower = (backendSignal.state || "").toLowerCase();
    
    if (["rising", "high", "bullish"].includes(stateLower)) {
        severity = backendSignal.signal.includes("Volatility") ? "negative" : "positive";
    } else if (["falling", "low", "bearish"].includes(stateLower)) {
        severity = backendSignal.signal.includes("Volatility") ? "positive" : "negative";
    }

    return {
        title: `${backendSignal.signal}: ${backendSignal.state}`,
        summary: backendSignal.portfolio_effect,
        confidence: backendSignal.confidence || 0.5,
        source: backendSignal.source || "System",
        severity: severity // "positive", "negative", "neutral"
    };
}

export function computeOverallConfidence(signals, dataFreshnessMinutes) {
    if (!signals || signals.length === 0) return { level: "Limited Data", score: 0 };
    
    const avgConfidence = signals.reduce((acc, s) => acc + (s.confidence || 0.5), 0) / signals.length;
    
    // Penalize confidence if data is stale
    let freshnessPenalty = 0;
    if (dataFreshnessMinutes > 60) freshnessPenalty = 0.1;
    if (dataFreshnessMinutes > 240) freshnessPenalty = 0.3;
    
    const finalScore = Math.max(0, avgConfidence - freshnessPenalty);
    
    if (finalScore >= 0.8) return { level: "High Confidence", score: finalScore };
    if (finalScore >= 0.5) return { level: "Moderate Confidence", score: finalScore };
    return { level: "Limited Data", score: finalScore };
}
