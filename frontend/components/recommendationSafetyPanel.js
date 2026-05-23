/**
 * Recommendation Safety Panel
 */

export function renderRecommendationSafetyPanel() {
    return `
    <div class="glass-panel p-4 border border-outline-variant/30 relative overflow-hidden h-full">
        <h3 class="label-md uppercase text-text-secondary mb-3 flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px] text-primary">verified_user</span>
            Why This Is Safe
        </h3>
        <ul class="space-y-2 body-sm text-on-surface">
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">check_circle</span>
                <span>Allocation generated deterministically via Mean-Variance Optimization</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">check_circle</span>
                <span>Market snapshot schema-validated (Pydantic)</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">check_circle</span>
                <span>AI reasoning strictly retrieval-grounded (Semantic FAISS)</span>
            </li>
            <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5">check_circle</span>
                <span>Confidence adjusted for stale data and signal disagreement</span>
            </li>
        </ul>
        <div class="absolute -right-4 -bottom-4 opacity-5">
            <span class="material-symbols-outlined text-[80px]">gavel</span>
        </div>
    </div>
    `;
}
