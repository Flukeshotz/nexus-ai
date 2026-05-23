/**
 * Scenario Simulator UX
 * Allows interactive market stress testing to trace portfolio delta.
 */
import { state, updateState } from '../state/appState.js';

export function renderScenarioSimulator() {
    return `
    <div class="glass-panel p-4 mb-6 border border-outline-variant/50">
        <h3 class="label-md uppercase text-text-secondary mb-3 flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px]">science</span>
            Macro Stress Test Simulator
        </h3>
        <div class="flex flex-wrap gap-2">
            <button class="chip chip-neutral hover:bg-market-down hover:text-white transition-colors" onclick="simulateScenario('inflation_spike')">🔥 Inflation Spike</button>
            <button class="chip chip-neutral hover:bg-market-neutral hover:text-white transition-colors" onclick="simulateScenario('recession')">📉 Recession</button>
            <button class="chip chip-neutral hover:bg-market-up hover:text-white transition-colors" onclick="simulateScenario('tech_boom')">🚀 Tech Boom</button>
            <button class="chip chip-neutral hover:bg-market-down hover:text-white transition-colors" onclick="simulateScenario('volatility_crash')">⚡ Volatility Crash</button>
        </div>
    </div>
    `;
}

export function handleScenarioSimulation(scenario) {
    const current = { ...state.marketSnapshot };
    let newSnapshot = { ...current, timestamp: new Date().toISOString() };
    let newSignals = [];

    if (scenario === 'inflation_spike') {
        newSnapshot.inflation_trend = "Rising Rapidly";
        newSnapshot.interest_rate_trend = "Hawkish";
        newSnapshot.market_regime = "Bearish";
        newSignals = [
            { signal: "Inflation Trend", state: "Rising Rapidly", portfolio_effect: "Maximized Gold & Real Asset Exposure", confidence: 0.92, source: "FRED CPIAUCSL" },
            { signal: "Interest Rates", state: "Hawkish", portfolio_effect: "Reduced Long Duration Bonds", confidence: 0.85, source: "Federal Reserve" }
        ];
    } else if (scenario === 'recession') {
        newSnapshot.market_regime = "Bearish";
        newSnapshot.volatility_level = "High";
        newSnapshot.fear_greed_score = 20;
        newSignals = [
            { signal: "Market Regime", state: "Bearish", portfolio_effect: "Shifted to Defensive Sectors (FMCG/Pharma)", confidence: 0.89, source: "yfinance SMA" },
            { signal: "Volatility", state: "High", portfolio_effect: "Increased Cash/Liquid Reserves", confidence: 0.95, source: "VIX" }
        ];
    } else if (scenario === 'tech_boom') {
        newSnapshot.market_regime = "Bullish";
        newSnapshot.volatility_level = "Low";
        newSnapshot.fear_greed_score = 85;
        newSignals = [
            { signal: "Sector Momentum", state: "Technology Surging", portfolio_effect: "Overweighted Tech Equities", confidence: 0.91, source: "NASDAQ Trend" },
            { signal: "Market Regime", state: "Bullish", portfolio_effect: "Minimized Cash Drag", confidence: 0.88, source: "yfinance SMA" }
        ];
    } else if (scenario === 'volatility_crash') {
        newSnapshot.volatility_level = "Extreme";
        newSnapshot.fear_greed_score = 10;
        newSignals = [
            { signal: "Volatility", state: "Extreme", portfolio_effect: "Triggered Circuit Breaker Protocol (Max Safe Assets)", confidence: 0.98, source: "VIX" }
        ];
    }

    // Update state causing UI to re-render Portfolio Evolution Timeline, Summary, and Cards
    updateState({
        previousSnapshot: current,
        marketSnapshot: newSnapshot,
        explainability: newSignals
    });

    // Optionally re-generate portfolio based on new state
    if (window.generatePortfolio) window.generatePortfolio();
}
