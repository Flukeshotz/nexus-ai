/**
 * Global Error Boundary Utility
 * Surface all errors gracefully — no silent crashes, no infinite spinners.
 */

export function showToast(message, type = 'error', durationMs = 5000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed; bottom: 24px; right: 24px; z-index: 9999;
            display: flex; flex-direction: column; gap: 10px; pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const icons = { error: 'error', warning: 'warning', success: 'check_circle', info: 'info' };
    const colors = {
        error: 'var(--market-down, #f44336)',
        warning: 'var(--market-neutral, #ff9800)',
        success: 'var(--market-up, #4caf50)',
        info: 'var(--primary, #6750a4)'
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: var(--surface-card, #1c1b1f); border: 1px solid ${colors[type]}44;
        color: var(--on-surface, #e6e1e5); border-left: 3px solid ${colors[type]};
        padding: 12px 16px; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        display: flex; align-items: center; gap: 10px; font-family: inherit;
        font-size: 13px; max-width: 360px; pointer-events: all;
        opacity: 0; transform: translateX(20px);
        transition: opacity 0.3s ease, transform 0.3s ease;
    `;

    toast.innerHTML = `
        <span class="material-symbols-outlined" style="color:${colors[type]};font-size:18px;">${icons[type]}</span>
        <span style="flex:1;">${message}</span>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        setTimeout(() => toast.remove(), 300);
    }, durationMs);
}

export function showLoadingOverlay(elementId, text = 'Processing...') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:40px;">
            <span class="material-symbols-outlined animate-pulse" style="font-size:40px;color:var(--primary)">psychology</span>
            <p style="color:var(--on-surface-variant);font-size:14px;">${text}</p>
        </div>
    `;
}

export function clearLoadingOverlay(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.innerHTML = '';
}

// Global uncaught error handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('[Global] Unhandled Promise Rejection:', event.reason);
    showToast('An unexpected error occurred. The system is operating in degraded mode.', 'warning');
});

window.addEventListener('error', (event) => {
    console.error('[Global] Uncaught Error:', event.message);
    // Only show toast if it's not a known resource load failure (images, etc)
    if (!event.filename || event.filename.includes('.js')) {
        showToast('A script error was detected. Some features may be limited.', 'warning');
    }
});
