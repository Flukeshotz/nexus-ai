/**
 * Loading State Manager
 * Provides rich, contextual loading states for all async operations.
 */

const LOADING_CONFIGS = {
    portfolio: {
        icon: 'psychology',
        title: 'Quantitative Engine Running',
        subtitle: 'Applying Ledoit-Wolf shrinkage and Mean-Variance Optimization...',
        steps: [
            'Fetching historical price data...',
            'Computing covariance matrix...',
            'Optimizing Sharpe Ratio...',
            'Applying market-aware adjustments...',
            'Generating explainability payload...'
        ]
    },
    chat: {
        icon: 'smart_toy',
        title: 'AI Reasoning',
        subtitle: 'Retrieving grounded context from semantic database...',
        steps: []
    },
    market: {
        icon: 'satellite_alt',
        title: 'Fetching Market Snapshot',
        subtitle: 'Ingesting live macro data from FRED and yfinance...',
        steps: []
    },
    demo: {
        icon: 'play_circle',
        title: 'Initializing Demo Mode',
        subtitle: 'Preloading investor profile and market scenario...',
        steps: []
    }
};

let stepInterval = null;

export function renderLoadingCard(type = 'portfolio') {
    const config = LOADING_CONFIGS[type] || LOADING_CONFIGS.portfolio;
    const stepsHtml = config.steps.length > 0 ? `
        <div id="loading-steps" style="
            margin-top:16px; font-size:12px; color:var(--on-surface-variant,#cac4d0);
            font-family:monospace; text-align:left; max-width:320px;
        ">
            <span id="loading-step-text">${config.steps[0]}</span>
        </div>` : '';

    return `
    <div style="
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        min-height:300px; gap:20px; padding:40px;
        animation: fadeIn 0.4s ease;
    ">
        <div style="position:relative;">
            <span class="material-symbols-outlined" style="
                font-size:56px; color:var(--primary,#6750a4);
                display:block;
                animation: pulse 2s ease-in-out infinite;
            ">${config.icon}</span>
            <div style="
                position:absolute; inset:-8px; border-radius:50%;
                border:2px solid var(--primary,#6750a4);
                border-top-color:transparent;
                animation: spin 1s linear infinite;
            "></div>
        </div>
        <div style="text-align:center;">
            <h3 style="color:var(--on-surface,#e6e1e5); margin:0 0 6px; font-size:18px;">${config.title}</h3>
            <p style="color:var(--on-surface-variant,#cac4d0); margin:0; font-size:13px;">${config.subtitle}</p>
        </div>
        ${stepsHtml}
    </div>`;
}

export function startLoadingSteps(type = 'portfolio') {
    const config = LOADING_CONFIGS[type];
    if (!config || !config.steps.length) return;

    let step = 0;
    stepInterval = setInterval(() => {
        step = (step + 1) % config.steps.length;
        const el = document.getElementById('loading-step-text');
        if (el) el.textContent = config.steps[step];
        else clearInterval(stepInterval);
    }, 1200);
}

export function clearLoadingSteps() {
    if (stepInterval) {
        clearInterval(stepInterval);
        stepInterval = null;
    }
}
