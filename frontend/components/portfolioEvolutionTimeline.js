/**
 * Portfolio Evolution Timeline Component
 */

export function renderPortfolioEvolutionTimeline(previousSnapshot, currentSnapshot, llmReasoningDelta) {
    if (!previousSnapshot || !currentSnapshot) {
        return `<div class="p-4 body-sm text-text-secondary">Historical timeline data accumulating. Please check back after next rebalancing cycle.</div>`;
    }

    // Identify what changed
    const changes = [];
    if (previousSnapshot.market_regime !== currentSnapshot.market_regime) {
        changes.push({ metric: "Market Regime", from: previousSnapshot.market_regime, to: currentSnapshot.market_regime });
    }
    if (previousSnapshot.inflation_trend !== currentSnapshot.inflation_trend) {
        changes.push({ metric: "Inflation Trend", from: previousSnapshot.inflation_trend, to: currentSnapshot.inflation_trend });
    }
    if (previousSnapshot.volatility_level !== currentSnapshot.volatility_level) {
        changes.push({ metric: "Volatility", from: previousSnapshot.volatility_level, to: currentSnapshot.volatility_level });
    }
    
    if (changes.length === 0) {
        changes.push({ metric: "Overall State", from: "Stable", to: "Stable" });
    }

    // Build timeline UI
    const today = new Date(currentSnapshot.timestamp || Date.now()).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const prevDate = new Date(previousSnapshot.timestamp || Date.now() - 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    let changesHtml = changes.map(c => 
        `<span class="chip bg-surface-variant border-none text-[12px]"><span class="text-text-secondary">${c.metric}:</span> ${c.from} → <strong class="text-primary">${c.to}</strong></span>`
    ).join(' ');

    return `
    <div class="glass-panel p-6 border-l-4 border-primary">
        <h3 class="headline-sm mb-4 flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">timeline</span>
            Portfolio Evolution
        </h3>
        
        <div class="relative pl-6 border-l border-outline-variant/50 space-y-6">
            
            <!-- Current Event -->
            <div class="relative">
                <div class="absolute -left-[30px] top-1 w-3 h-3 rounded-full bg-primary ring-4 ring-surface-container-highest"></div>
                <div class="mb-1 flex items-center gap-2">
                    <span class="label-md font-bold text-text-primary uppercase tracking-wider">${today} — Allocation Adjusted</span>
                </div>
                <div class="flex flex-wrap gap-2 mb-3">
                    ${changesHtml}
                </div>
                <div class="p-3 bg-surface-container/50 border border-outline-variant/30 rounded-lg body-sm text-on-surface-variant">
                    ${llmReasoningDelta ? llmReasoningDelta : "AI quantitative engine re-balanced portfolio weights strictly adhering to target volatility bands."}
                </div>
            </div>
            
            <!-- Previous Event -->
            <div class="relative opacity-60">
                <div class="absolute -left-[30px] top-1 w-3 h-3 rounded-full bg-surface-variant ring-4 ring-surface-container-highest"></div>
                <div class="mb-1 flex items-center gap-2">
                    <span class="label-md font-bold text-text-primary uppercase tracking-wider">${prevDate} — Baseline Established</span>
                </div>
                <div class="p-3 bg-transparent border border-outline-variant/30 rounded-lg body-sm text-text-secondary">
                    Initial portfolio constructed based on ${previousSnapshot.market_regime} regime and user risk tolerances.
                </div>
            </div>

        </div>
    </div>
    `;
}
