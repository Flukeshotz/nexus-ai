/**
 * Demo Mode Orchestrator
 * Scripts the ideal onboarding -> snapshot -> portfolio -> reasoning PM flow.
 */

import { updateState } from '../state/appState.js';

let overlayElement = null;

function showCommentary(text, duration = 3000) {
    if (!overlayElement) {
        overlayElement = document.createElement('div');
        overlayElement.className = 'fixed bottom-10 left-1/2 transform -translate-x-1/2 z-50 bg-primary text-on-primary px-6 py-3 rounded-full shadow-2xl font-body-md font-medium animate-fade-in text-center max-w-[80%] pointer-events-none';
        document.body.appendChild(overlayElement);
    }
    overlayElement.innerHTML = `<span class="material-symbols-outlined align-middle mr-2 text-[20px]">smart_toy</span> ${text}`;
    overlayElement.style.opacity = 1;
    
    if (window.commentaryTimeout) clearTimeout(window.commentaryTimeout);
    window.commentaryTimeout = setTimeout(() => {
        overlayElement.style.opacity = 0;
    }, duration);
}

export function startDemoFlow() {
    console.log("Starting PM Demo Flow...");
    showCommentary("Initializing Demo Flow: Preloading Investor Profile...", 2000);

    // Step 1: Preload investor profile
    document.getElementById('ob-age').value = 24;
    document.getElementById('ob-horizon').value = "long_term";
    if (window.selectRisk) window.selectRisk('aggressive');

    // Step 2: Set an interesting market state
    setTimeout(() => {
        showCommentary("Injecting Live Market Snapshot: Detecting Bullish Regime...", 2500);
        updateState({
            marketSnapshot: {
                timestamp: new Date().toISOString(),
                market_regime: "Bullish",
                inflation_trend: "Rising",
                interest_rate_trend: "Stable",
                volatility_level: "Moderate",
                fear_greed_score: 75
            },
            previousSnapshot: {
                timestamp: new Date(Date.now() - 86400000).toISOString(),
                market_regime: "Neutral",
                inflation_trend: "Stable",
                volatility_level: "Low",
                fear_greed_score: 50
            },
            explainability: [
                { signal: "Inflation Trend", state: "Rising", portfolio_effect: "Increased Gold Allocation by 5%", confidence: 0.88, source: "FRED CPIAUCSL" },
                { signal: "Market Regime", state: "Bullish", portfolio_effect: "Overweighted NIFTYBEES", confidence: 0.95, source: "yfinance 50-SMA" }
            ]
        });
    }, 2000);

    // Step 3: Trigger Profile Save & Portfolio Generation
    setTimeout(() => {
        showCommentary("Generating Explainable Portfolio via Deterministic Engine...", 3000);
        if (window.saveProfile) window.saveProfile();
        
        // Wait for generation to finish then trigger chat question
        setTimeout(() => {
            showCommentary("Notice the Portfolio Timeline translating macro signals into UI narratives.", 3500);
            
            setTimeout(() => {
                if (window.toggleChat) window.toggleChat();
                showCommentary("Initiating Conversational Audit...", 2000);
                setTimeout(() => {
                    if (window.sendSuggestion) window.sendSuggestion("Why did my portfolio change?");
                }, 1000);
            }, 4000);
        }, 2500);

    }, 4500);
}
