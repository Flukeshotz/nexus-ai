/**
 * Daily Market Summary Component
 */

export function renderDailyMarketSummary(snapshot) {
    if (!snapshot) {
        return `<div class="insight-card border-l-4 border-outline-variant">
            <h4 class="headline-sm mb-2">Market Data Unavailable</h4>
            <p class="body-sm text-text-secondary">Waiting for live data feed...</p>
        </div>`;
    }

    const { market_regime, inflation_trend, interest_rate_trend, volatility_level, fear_greed_score } = snapshot;
    
    let borderColor = "var(--primary)";
    if (market_regime === "Bearish" || volatility_level === "High") {
        borderColor = "var(--market-down)";
    } else if (market_regime === "Neutral") {
        borderColor = "var(--market-neutral)";
    }

    let freshnessMin = 0;
    if (snapshot.timestamp) {
        freshnessMin = Math.round((new Date() - new Date(snapshot.timestamp)) / 60000);
    }

    return `
    <div class="insight-card border-l-4 relative overflow-hidden h-full" style="border-left-color: ${borderColor}">
        <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-sm">
                <span class="material-symbols-outlined text-primary-c">language</span>
                <h4 class="headline-sm">Today's Macro Narrative</h4>
            </div>
            <span class="label-md bg-surface-container px-2 py-1 rounded text-text-secondary border border-outline-variant/30 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full ${freshnessMin < 60 ? 'bg-primary' : 'bg-market-neutral'}"></span>
                Updated ${freshnessMin}m ago
            </span>
        </div>
        
        <ul class="space-y-2 body-sm text-on-surface">
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">adjust</span>
                <span>The broader market is currently exhibiting a <strong>${market_regime}</strong> trend structure.</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">adjust</span>
                <span>Inflation pressures are marked as <strong>${inflation_trend}</strong>, influencing intermediate-term asset pricing.</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">adjust</span>
                <span>Overall market volatility is <strong>${volatility_level}</strong> (Fear & Greed Index: ${fear_greed_score}/100).</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">adjust</span>
                <span>Interest rate trajectories appear <strong>${interest_rate_trend}</strong>, affecting fixed income yields.</span>
            </li>
        </ul>
        
        <div class="absolute right-2 bottom-2 opacity-5">
            <span class="material-symbols-outlined text-[64px]">account_balance</span>
        </div>
    </div>
    `;
}
