/**
 * Portfolio Narrative Engine
 * Translates quantitative allocations and market state into human-friendly PM narratives.
 */

export function generatePortfolioNarrative(portfolioData, marketSnapshot) {
    if (!portfolioData || !marketSnapshot) return "Awaiting sufficient data to generate narrative.";

    const regime = (marketSnapshot.market_regime || "Neutral").toLowerCase();
    const inflation = (marketSnapshot.inflation_trend || "Stable").toLowerCase();
    
    // Sort weights to find top allocations
    const weights = portfolioData.weights || {};
    const topAssets = Object.entries(weights)
        .filter(([_, w]) => w > 0.05)
        .sort((a, b) => b[1] - a[1])
        .map(([asset, _]) => asset.replace('.NS', ''));

    let primaryFocus = "diversified assets";
    if (topAssets.includes("NIFTYBEES") || topAssets.includes("RELIANCE")) {
        primaryFocus = "growth-oriented equity exposure";
    } else if (topAssets.includes("LIQUIDBEES")) {
        primaryFocus = "capital preservation via liquid assets";
    }

    let justification = "to balance potential returns with risk.";
    if (regime === "bearish") {
        justification = "because market regime indicators suggest downside risk, prioritizing stability.";
    } else if (regime === "bullish" && inflation === "rising") {
        justification = "because equity momentum remains strong despite rising inflation pressures.";
    } else if (inflation === "falling") {
        justification = "because easing inflation provides a tailwind for broader market expansion.";
    }

    return `Your portfolio currently favors <strong>${primaryFocus}</strong> ${justification}`;
}
