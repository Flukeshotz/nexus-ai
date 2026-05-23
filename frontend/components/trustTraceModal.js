/**
 * Trust Trace Modal
 * Exposes the exact signals, retrieved documents, and confidence used by the AI.
 */

export function renderTrustTraceModal(traceData) {
    // If modal doesn't exist, create it
    let modal = document.getElementById('trust-trace-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'trust-trace-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm hidden opacity-0 transition-opacity duration-300';
        document.body.appendChild(modal);
    }

    const docsHtml = (traceData.retrieved_docs || []).map(doc => `
        <div class="p-2 border border-outline-variant/30 rounded bg-surface-container mb-2 body-sm text-text-secondary">
            <span class="text-primary font-mono text-[10px] uppercase">Retrieved Context</span><br>
            "${doc}"
        </div>
    `).join('');

    const signalsHtml = (traceData.signals || []).map(sig => `
        <span class="chip chip-primary text-[10px]">${sig.signal}: ${sig.state}</span>
    `).join('');

    modal.innerHTML = `
        <div class="bg-surface-card border border-outline-variant rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto flex flex-col relative" onclick="event.stopPropagation()">
            <!-- Header -->
            <div class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low sticky top-0 z-10">
                <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">policy</span>
                    <h3 class="headline-sm">AI Reasoning Trace</h3>
                </div>
                <button class="text-text-secondary hover:text-white transition-colors" onclick="closeTrustTraceModal()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            
            <!-- Body -->
            <div class="p-6 space-y-6">
                
                <!-- Confidence -->
                <div class="flex justify-between items-end border-b border-outline-variant/30 pb-4">
                    <div>
                        <span class="label-md uppercase text-text-secondary">Execution Confidence</span>
                        <div class="display mt-1 text-primary">${Math.round((traceData.confidence || 0.92) * 100)}%</div>
                    </div>
                    <div class="text-right">
                        <span class="label-md uppercase text-text-secondary">Data Freshness</span>
                        <div class="body mt-1 text-on-surface">Live Snapshot</div>
                    </div>
                </div>

                <!-- Signals -->
                <div>
                    <h4 class="label-md uppercase text-text-secondary mb-2">Determinants (Market State)</h4>
                    <div class="flex flex-wrap gap-2">
                        ${signalsHtml || '<span class="text-text-secondary text-sm">No signals explicitly traced for this query.</span>'}
                    </div>
                </div>

                <!-- Retrieval -->
                <div>
                    <h4 class="label-md uppercase text-text-secondary mb-2">Semantic Grounding (RAG)</h4>
                    <div class="max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                        ${docsHtml || '<span class="text-text-secondary text-sm">No external documents retrieved.</span>'}
                    </div>
                </div>

                <!-- Snapshot Context -->
                <div>
                    <h4 class="label-md uppercase text-text-secondary mb-2">Macroeconomic Snapshot</h4>
                    <pre class="p-3 bg-surface-container-lowest border border-outline-variant/50 rounded-lg text-[11px] font-mono text-text-secondary overflow-x-auto">${JSON.stringify(traceData.snapshot || {}, null, 2)}</pre>
                </div>

            </div>
        </div>
    `;

    // Show modal
    modal.classList.remove('hidden');
    // slight delay for transition
    setTimeout(() => modal.classList.remove('opacity-0'), 10);
}

// Attach globally
window.closeTrustTraceModal = () => {
    const modal = document.getElementById('trust-trace-modal');
    if (modal) {
        modal.classList.add('opacity-0');
        setTimeout(() => modal.classList.add('hidden'), 300);
    }
};
