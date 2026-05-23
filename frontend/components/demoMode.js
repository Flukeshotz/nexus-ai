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
    console.log("Starting PM Showcase Flow...");
    showCommentary("Welcome to Nexus AI. Loading Deterministic Portfolio Vault...", 3000);

    // Step 1: Preload and scan
    setTimeout(() => {
        showCommentary("Scanning Live Macro Data... Fresh Snapshot Active.", 3500);
        updateState({
            marketSnapshot: {
                timestamp: new Date().toISOString(),
                market_regime: "Bullish",
                inflation_trend: "Rising",
                interest_rate_trend: "Stable",
                volatility_level: "Moderate",
                fear_greed_score: 75
            }
        });
    }, 3500);

    // Step 2: Highlight proactive intelligence
    setTimeout(() => {
        showCommentary("Smart Alerts triggered. Checking for Portfolio Drift...", 3500);
    }, 7500);

    // Step 3: Call to action for scenario simulation
    setTimeout(() => {
        showCommentary("Navigate to 'AI Strategies' or run a Scenario Simulation to continue the demo.", 5000);
    }, 11500);
}
