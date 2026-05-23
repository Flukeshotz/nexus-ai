/**
 * AI Confidence Meter Component
 */
import { computeOverallConfidence } from '../services/explainabilityAdapter.js';

export function renderAIConfidenceMeter(rawSignals, dataFreshnessMinutes = 0) {
    const { level, score } = computeOverallConfidence(rawSignals, dataFreshnessMinutes);
    const scorePct = Math.round(score * 100);
    
    let colorClass = "bg-market-neutral";
    let icon = "help";
    let textClass = "text-market-neutral";
    
    if (score >= 0.8) {
        colorClass = "bg-primary";
        textClass = "text-primary";
        icon = "verified_user";
    } else if (score >= 0.5) {
        colorClass = "bg-tertiary";
        textClass = "text-tertiary";
        icon = "security";
    } else {
        colorClass = "bg-market-down";
        textClass = "text-market-down";
        icon = "warning";
    }

    let reasonText = "All signals aligned and current.";
    if (dataFreshnessMinutes > 240) {
        reasonText = "Stale market snapshot data.";
    } else if (score < 0.8 && score >= 0.5) {
        reasonText = "Elevated signal disagreement detected.";
    } else if (score < 0.5) {
        reasonText = "Insufficient retrieved context or highly conflicting signals.";
    }

    return `
    <div class="glass-panel p-4 flex flex-col gap-sm relative overflow-hidden h-full">
        <div class="flex justify-between items-center z-10">
            <h3 class="label-md uppercase text-text-secondary">AI Confidence Score</h3>
            <span class="material-symbols-outlined ${textClass} text-[18px]">${icon}</span>
        </div>
        
        <div class="flex items-end gap-2 z-10">
            <span class="font-display-lg text-[32px] leading-none ${textClass}">${scorePct}%</span>
            <span class="body-sm text-text-secondary pb-1">${level}</span>
        </div>
        
        <div class="progress-bar mt-2 z-10">
            <div class="progress-fill ${colorClass} transition-all duration-1000 ease-out" style="width: ${scorePct}%"></div>
        </div>
        
        <div class="mt-3 pt-3 border-t border-outline-variant/30 z-10">
            <span class="label-md uppercase text-text-secondary block mb-1">Reasoning</span>
            <span class="body-sm text-on-surface-variant">${reasonText}</span>
        </div>
        
        <!-- Subtle Glow Background -->
        <div class="absolute -right-4 -bottom-4 w-24 h-24 rounded-full ${colorClass} opacity-10 blur-[20px] pointer-events-none"></div>
    </div>
    `;
}
