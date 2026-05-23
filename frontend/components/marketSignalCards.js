/**
 * Market Signal Cards Component
 */
import { normalizeSignal } from '../services/explainabilityAdapter.js';

export function renderMarketSignalCards(rawSignals) {
    if (!rawSignals || rawSignals.length === 0) {
        return `<div class="p-4 body-sm text-text-secondary border border-outline-variant/30 rounded-lg">No market signals available.</div>`;
    }

    const cardsHtml = rawSignals.map(sig => {
        const normalized = normalizeSignal(sig);
        
        // Map severity to our CSS vars
        let icon = "info";
        let colorClass = "text-market-neutral";
        if (normalized.severity === "positive") {
            icon = "trending_up";
            colorClass = "text-market-up";
        } else if (normalized.severity === "negative") {
            icon = "trending_down";
            colorClass = "text-market-down";
        }

        const confidencePct = Math.round(normalized.confidence * 100);

        return `
        <div class="insight-card border border-outline-variant/30 bg-surface-container/50 hover:bg-surface-container transition-colors relative overflow-hidden group">
            <div class="flex items-start justify-between mb-2">
                <div class="flex items-center gap-sm">
                    <span class="material-symbols-outlined ${colorClass} text-[20px]">${icon}</span>
                    <h4 class="headline-sm font-semibold">${normalized.title}</h4>
                </div>
                <div class="flex flex-col items-end">
                    <span class="label-md text-text-secondary">Confidence</span>
                    <span class="mono-stats ${confidencePct > 80 ? 'text-primary' : 'text-text-secondary'}">${confidencePct}%</span>
                </div>
            </div>
            
            <p class="body-sm text-on-surface mb-3">
                ${normalized.summary}
            </p>
            
            <div class="flex justify-between items-center mt-auto pt-2 border-t border-outline-variant/20">
                <span class="label-md text-text-secondary flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">database</span>
                    ${normalized.source}
                </span>
            </div>
            
            <!-- Subtle Hover Gradient -->
            <div class="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity"></div>
        </div>
        `;
    }).join('');

    return `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
        ${cardsHtml}
    </div>
    `;
}
