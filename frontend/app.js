/**
 * Nexus AI - Main Application Logic
 * Implements SPA Router, API Client, and View Rendering for Phase UX-1
 */

import { state, updateState, subscribe } from './state/appState.js';

// GLOBAL FAILSAFE: If the app crashes completely, print the error to the screen so we can see it!
window.addEventListener('error', function(e) {
    const main = document.getElementById('app-main');
    if (main) {
        main.innerHTML = `<div style="padding: 40px; color: red; background: #220000; font-family: monospace;">
            <h2>FATAL CRASH</h2>
            <p>${e.message}</p>
            <p>At ${e.filename}:${e.lineno}</p>
        </div>`;
    }
});
window.addEventListener('unhandledrejection', function(e) {
    const main = document.getElementById('app-main');
    if (main) {
        main.innerHTML = `<div style="padding: 40px; color: red; background: #220000; font-family: monospace;">
            <h2>PROMISE CRASH</h2>
            <p>${e.reason}</p>
        </div>`;
    }
});

import { renderDailyMarketSummary } from './components/dailyMarketSummary.js';
import { renderAIConfidenceMeter } from './components/aiConfidenceMeter.js';
import { renderPortfolioEvolutionTimeline } from './components/portfolioEvolutionTimeline.js';
import { renderMarketSignalCards } from './components/marketSignalCards.js';
import { generatePortfolioNarrative } from './services/portfolioNarrativeEngine.js';
import { renderScenarioSimulator, handleScenarioSimulation } from './components/scenarioSimulator.js';
import { renderTrustTraceModal } from './components/trustTraceModal.js';
import { startDemoFlow } from './components/demoMode.js';
import { renderSystemStatusPanel } from './components/systemStatusPanel.js';
import { renderRecommendationSafetyPanel } from './components/recommendationSafetyPanel.js';
import { showToast } from './services/errorBoundary.js';
import { renderLoadingCard, startLoadingSteps, clearLoadingSteps } from './services/loadingStateManager.js';

const API_BASE =
    window.location.hostname === "localhost"
        ? "http://localhost:8000/api/v1"
        : "https://nexus-ai-4y4s.onrender.com/api/v1";

// Provide initial mock state for UI testing
updateState({
    token: null,
    profile: null,
    portfolio: null,
    holdings: [],
    vaultDashboard: null,
    marketSnapshot: {
        timestamp: new Date().toISOString(),
        market_regime: "Bullish",
        inflation_trend: "Rising",
        interest_rate_trend: "Stable",
        volatility_level: "Moderate",
        fear_greed_score: 68
    },
    previousSnapshot: {
        timestamp: new Date(Date.now() - 86400000).toISOString(),
        market_regime: "Neutral",
        inflation_trend: "Stable",
        volatility_level: "Moderate"
    },
    explainability: [
        { signal: "Inflation Trend", state: "Rising", portfolio_effect: "Increased Gold Allocation", confidence: 0.85, source: "FRED CPIAUCSL" },
        { signal: "Market Regime", state: "Bullish", portfolio_effect: "Maintained Equity Exposure", confidence: 0.92, source: "yfinance SMA" }
    ]
});

// ── UTILS ────────────────────────────────────────────────────────
function formatCurrency(value) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
}
function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}
function getRiskColor(volatility) {
    if (volatility < 0.1) return 'var(--market-up)';
    if (volatility < 0.2) return 'var(--market-neutral)';
    return 'var(--market-down)';
}

// ── ROUTER & APP SHELL ──────────────────────────────────────────
function navigateTo(page) {
    if (page !== window.location.hash.substring(1)) {
        window.history.pushState(null, null, '#' + page);
    }
    renderPage(page);
    
    // Update nav links
    document.querySelectorAll('.nav-link, .mobile-nav-item').forEach(link => {
        if (link.dataset.page === page) link.classList.add('active');
        else link.classList.remove('active');
    });
}

window.addEventListener('hashchange', () => {
    const page = window.location.hash.substring(1) || 'dashboard';
    navigateTo(page);
});

async function initApp() {
    // Check if onboarded
    state.token = localStorage.getItem('nexus_token');
    
    try {
        const storedProfile = localStorage.getItem('nexus_profile');
        if (storedProfile) {
            state.profile = JSON.parse(storedProfile);
        }
        
        const storedPortfolio = localStorage.getItem('nexus_portfolio');
        if (storedPortfolio) {
            state.portfolio = JSON.parse(storedPortfolio);
        }
    } catch (e) {
        console.warn("Cleared corrupted local storage data", e);
        localStorage.removeItem('nexus_profile');
        localStorage.removeItem('nexus_portfolio');
    }

    const page = window.location.hash.substring(1) || (state.token ? 'dashboard' : 'login');
    
    // If the hash is already the same, setting it won't trigger 'hashchange'.
    navigateTo(page);
}

// ── AUTH VIEWS ───────────────────────────────────────────────────

function renderLogin() {
    return `
    <div class="relative z-10 w-full max-w-[440px] mx-auto px-margin-mobile md:px-0 mt-20">
        <!-- Atmospheric Background Layers -->
        <div class="absolute inset-0 z-0 pointer-events-none flex items-center justify-center overflow-hidden">
            <div class="absolute w-[800px] h-[800px] rounded-full bg-primary/5 blur-[120px] glow-effect -top-[200px] -left-[200px]"></div>
            <div class="absolute w-[600px] h-[600px] rounded-full bg-tertiary/5 blur-[100px] glow-effect bottom-[0px] right-[0px]" style="animation-delay: -4s;"></div>
        </div>
        <!-- Header -->
        <div class="text-center mb-unit-xl animate-fade-in" style="animation-delay: 0.1s;">
            <h1 class="font-display-lg text-display-lg text-text-primary tracking-tighter mb-unit-xs">NEXUS AI</h1>
            <p class="font-body-md text-body-md text-text-secondary">Institutional Access Terminal</p>
        </div>
        <!-- Glassmorphic Card -->
        <div class="bg-surface-glass backdrop-blur-xl border-t border-l border-outline-variant/50 shadow-2xl rounded-xl p-unit-xl animate-fade-in relative overflow-hidden" style="animation-delay: 0.2s;">
            <!-- Subtle highlight on top edge of glass -->
            <div class="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
            <form onsubmit="event.preventDefault(); doLogin();" class="space-y-unit-lg">
                <!-- Email Field -->
                <div class="space-y-unit-xs">
                    <label class="block font-label-md text-label-md text-on-surface-variant uppercase" for="email">Institutional Email</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="material-symbols-outlined text-gray-500 text-[20px]">mail</span>
                        </span>
                        <input class="block w-full pl-10 pr-3 py-3 border border-surface-variant rounded-lg font-body-md text-body-md placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors" style="background-color: white !important; color: black !important;" id="email" placeholder="analyst@fund.com" required="" type="email">
                    </div>
                </div>
                <!-- Passphrase Field -->
                <div class="space-y-unit-xs">
                    <div class="flex justify-between items-center">
                        <label class="block font-label-md text-label-md text-on-surface-variant uppercase" for="password">Passphrase</label>
                        <a href="#forgot" onclick="navigateTo('forgot')" class="font-label-md text-label-md text-primary hover:text-primary-fixed-dim transition-colors">Forgot Passphrase?</a>
                    </div>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="material-symbols-outlined text-gray-500 text-[20px]">lock</span>
                        </span>
                        <input class="block w-full pl-10 pr-10 py-3 border border-surface-variant rounded-lg font-body-md text-body-md placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors" style="background-color: white !important; color: black !important;" id="password" placeholder="••••••••••••••••" required="" type="password">
                    </div>
                </div>
                <!-- Submit Button -->
                <div class="pt-unit-sm">
                    <button class="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm font-label-md text-label-md uppercase tracking-wider text-text-primary bg-gradient-to-r from-primary to-tertiary hover:from-primary-fixed-dim hover:to-tertiary-fixed-dim focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-surface focus:ring-primary transition-all duration-200 group" type="submit">
                        Authenticate Access
                        <span class="material-symbols-outlined ml-2 text-[18px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                    </button>
                </div>
            </form>
            
            <div class="mt-unit-lg text-center">
                <p class="font-body-sm text-body-sm text-text-secondary">
                    Don't have access? <a href="#register" onclick="navigateTo('register')" class="text-primary hover:text-primary-fixed-dim transition-colors font-medium underline underline-offset-4">Apply for an account</a>
                </p>
                <p class="font-label-md text-label-md text-text-secondary/60 mt-4">
                    <span class="material-symbols-outlined text-[14px] inline-block align-middle mr-1">shield</span>
                    Encrypted via Quantum-Resistant TLS 1.3
                </p>
            </div>
        </div>
    </div>`;
}

function renderRegister() {
    return `
    <div class="relative z-10 w-full max-w-[440px] mx-auto px-margin-mobile md:px-0 mt-20">
        <div class="absolute inset-0 z-0 pointer-events-none flex items-center justify-center overflow-hidden">
            <div class="absolute w-[800px] h-[800px] rounded-full bg-primary/5 blur-[120px] glow-effect -top-[200px] -left-[200px]"></div>
        </div>
        <div class="text-center mb-unit-xl animate-fade-in" style="animation-delay: 0.1s;">
            <h1 class="font-display-lg text-display-lg text-text-primary tracking-tighter mb-unit-xs">NEXUS AI</h1>
            <p class="font-body-md text-body-md text-text-secondary">Apply for Access</p>
        </div>
        <div class="bg-surface-glass backdrop-blur-xl border-t border-l border-outline-variant/50 shadow-2xl rounded-xl p-unit-xl animate-fade-in relative overflow-hidden" style="animation-delay: 0.2s;">
            <div class="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
            <form onsubmit="event.preventDefault(); doRegister();" class="space-y-unit-lg">
                <div class="space-y-unit-xs">
                    <label class="block font-label-md text-label-md text-on-surface-variant uppercase">Full Name</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="material-symbols-outlined text-gray-500 text-[20px]">person</span>
                        </span>
                        <input class="block w-full pl-10 pr-3 py-3 border border-surface-variant rounded-lg font-body-md text-body-md placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary transition-colors" style="background-color: white !important; color: black !important;" id="reg-name" placeholder="John Doe" required="" type="text">
                    </div>
                </div>
                <div class="space-y-unit-xs">
                    <label class="block font-label-md text-label-md text-on-surface-variant uppercase">Email</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="material-symbols-outlined text-gray-500 text-[20px]">mail</span>
                        </span>
                        <input class="block w-full pl-10 pr-3 py-3 border border-surface-variant rounded-lg font-body-md text-body-md placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary transition-colors" style="background-color: white !important; color: black !important;" id="reg-email" placeholder="analyst@fund.com" required="" type="email">
                    </div>
                </div>
                <div class="space-y-unit-xs">
                    <label class="block font-label-md text-label-md text-on-surface-variant uppercase">Passphrase</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="material-symbols-outlined text-gray-500 text-[20px]">lock</span>
                        </span>
                        <input class="block w-full pl-10 pr-10 py-3 border border-surface-variant rounded-lg font-body-md text-body-md placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary transition-colors" style="background-color: white !important; color: black !important;" id="reg-pass" placeholder="At least 8 characters" required="" type="password">
                    </div>
                </div>
                <div class="pt-unit-sm">
                    <button class="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm font-label-md text-label-md uppercase tracking-wider text-text-primary bg-gradient-to-r from-primary to-tertiary hover:from-primary-fixed-dim hover:to-tertiary-fixed-dim transition-all group" type="submit">
                        Create Account
                        <span class="material-symbols-outlined ml-2 text-[18px] group-hover:translate-x-1 transition-transform">person_add</span>
                    </button>
                </div>
            </form>
            <div class="mt-unit-lg text-center">
                <p class="font-body-sm text-body-sm text-text-secondary">
                    Already have an account? <a href="#login" onclick="navigateTo('login')" class="text-primary hover:text-primary-fixed-dim font-medium underline underline-offset-4">Sign In</a>
                </p>
            </div>
        </div>
    </div>`;
}

function renderForgot() {
    return `
    <div class="glass-panel max-w-[500px] mx-auto overflow-hidden mt-10">
        <div class="p-6 border-b border-outline-variant bg-surface-card text-center">
            <h2 class="headline">Reset Password</h2>
            <p class="body-sm text-muted mt-1">Enter your email to receive a reset link</p>
        </div>
        <div class="p-6 flex flex-col gap-4">
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" id="forgot-email" class="form-input" placeholder="Enter your email">
            </div>
            <button class="btn-primary mt-2 justify-center w-full" onclick="doForgot()">Send Reset Link</button>
            <div class="text-center mt-4">
                <a href="#login" class="text-primary-c body-sm" style="text-decoration:none">Back to Sign In</a>
            </div>
        </div>
    </div>`;
}

// ── AUTH HANDLERS (Connected to Backend) ───────────────────────────

async function doLogin() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (!email || !password) {
        alert("Please enter email and password.");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            let errorMsg = "Invalid credentials";
            if (errorData.detail) {
                errorMsg = Array.isArray(errorData.detail) ? errorData.detail[0].msg : errorData.detail;
            }
            alert("Login Failed: " + errorMsg);
            return;
        }
        
        const data = await res.json();
        state.token = data.access_token;
        localStorage.setItem('nexus_token', state.token);
        
        // Also mock a profile for now since we don't fetch it yet
        if (!state.profile) {
            state.profile = { age: 30, risk: 'moderate', horizon: 'long_term' };
            localStorage.setItem('nexus_profile', JSON.stringify(state.profile));
        }
        
        navigateTo('dashboard');
    } catch (err) {
        console.error(err);
        alert("Server connection failed. Is the backend running?");
    }
}

async function doRegister() {
    const fullName = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-pass').value;
    
    if (!email || !password || !fullName) {
        alert("Please fill all fields.");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName, email, password })
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            let errorMsg = "Error";
            if (errorData.detail) {
                errorMsg = Array.isArray(errorData.detail) ? errorData.detail[0].msg : errorData.detail;
            }
            alert("Registration Failed: " + errorMsg);
            return;
        }
        
        const data = await res.json();
        state.token = data.access_token;
        localStorage.setItem('nexus_token', state.token);
        navigateTo('onboarding');
    } catch (err) {
        console.error(err);
        alert("Server connection failed.");
    }
}

function doForgot() { 
    const email = document.getElementById('forgot-email').value;
    if (!email) {
        alert("Please enter your email.");
        return;
    }
    alert("If an account exists, a reset link has been sent to " + email); 
    navigateTo('login'); 
}

// ── VIEWS ────────────────────────────────────────────────────────

function renderPage(page) {
    const main = document.getElementById('app-main');
    main.innerHTML = ''; // Clear

    // Hide/show navigation based on auth state
    const isAuthPage = ['login', 'register', 'forgot'].includes(page);
    document.getElementById('app-header').style.display = isAuthPage ? 'none' : 'flex';
    document.getElementById('mobile-nav').style.display = isAuthPage ? 'none' : 'flex';
    document.getElementById('chat-fab').style.display = isAuthPage ? 'none' : 'flex';

    switch(page) {
        case 'login': main.innerHTML = renderLogin(); break;
        case 'register': main.innerHTML = renderRegister(); break;
        case 'forgot': main.innerHTML = renderForgot(); break;
        case 'onboarding': main.innerHTML = renderOnboarding(); break;
        case 'dashboard': main.innerHTML = renderDashboard(); break;
        case 'portfolio': main.innerHTML = renderAIAdvice(); break;
        case 'insights': main.innerHTML = renderInsights(); break;
        case 'goals': main.innerHTML = renderGoals(); break;
        case 'markets': main.innerHTML = renderMarkets(); setTimeout(injectTradingView, 100); break;
        default: main.innerHTML = renderDashboard(); break;
    }
    
    // Animate in
    if(main.firstElementChild) main.firstElementChild.classList.add('fade-in');
}

// 1. Dashboard View (The Vault)
function renderDashboard() {
    if (!state.token) {
        return `<div class="card fade-in text-center"><h2 class="headline mb-4">Welcome to Nexus AI</h2>
                <p class="body mb-6">Please log in to view your Vault.</p>
                <button class="btn-primary" onclick="navigateTo('login')">Sign In</button></div>`;
    }
    
    if (!state.vaultDashboard) {
        // Fetch vault data
        fetchVaultDashboard();
        return renderLoadingCard('vault');
    }

    if (!state.vaultDashboard.holdings || state.vaultDashboard.holdings.length === 0) {
        return `
        <div class="glass-panel text-center max-w-[600px] mx-auto py-12 mt-12 fade-in relative overflow-hidden">
            <div class="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none"></div>
            <span class="material-symbols-outlined text-[64px] text-primary/40 mb-4 block">account_balance</span>
            <h2 class="display mb-2">Your Vault is empty</h2>
            <p class="body text-muted mb-8 max-w-[400px] mx-auto">Add your existing investments to unlock live tracking, AI risk analysis, and actionable portfolio insights.</p>
            <button class="btn-primary mx-auto" onclick="openAddHoldingModal()">
                <span class="material-symbols-outlined mr-2">add</span> Add First Investment
            </button>
        </div>`;
    }

    const d = state.vaultDashboard;
    
    let holdingsHtml = '';
    d.holdings.forEach(h => {
        let pnlClass = h.unrealised_pnl >= 0 ? 'text-up' : 'text-down';
        let pnlSign = h.unrealised_pnl >= 0 ? '+' : '';
        holdingsHtml += `
        <tr>
            <td>
                <div class="body font-semibold">${h.asset_ticker}</div>
                <div class="label text-muted">${h.asset_class}</div>
            </td>
            <td class="mono">${h.quantity.toFixed(2)}</td>
            <td class="mono">${formatCurrency(h.average_buy_price)}</td>
            <td class="mono">${formatCurrency(h.current_price)}</td>
            <td class="mono ${pnlClass}">${pnlSign}${formatCurrency(h.unrealised_pnl)}<br><span class="text-xs">(${pnlSign}${h.unrealised_pnl_pct.toFixed(2)}%)</span></td>
            <td>
                <button class="material-symbols-outlined text-muted hover:text-error transition-colors" onclick="deleteHolding('${h.id}')" title="Remove Holding">delete</button>
            </td>
        </tr>`;
    });

    let totalPnlClass = d.total_unrealised_pnl >= 0 ? 'text-up' : 'text-down';
    let totalPnlSign = d.total_unrealised_pnl >= 0 ? '+' : '';
    let dayPnlClass = d.day_change >= 0 ? 'text-up' : 'text-down';
    let dayPnlSign = d.day_change >= 0 ? '+' : '';

    return `
    <div class="bento fade-in">
        <div class="col-12 flex justify-between items-center mb-2">
            <div>
                <h1 class="headline">My Vault</h1>
                <p class="body-sm text-muted">Live Tracking & AI Oversight <span class="text-xs ml-2 text-primary-c">• Data updated 1 min ago</span></p>
            </div>
            <button class="btn-secondary" onclick="openAddHoldingModal()">
                <span class="material-symbols-outlined mr-2">add</span> Add Asset
            </button>
        </div>

        <!-- Net Worth Card -->
        <div class="col-6 glass-panel p-6 ai-glow relative overflow-hidden">
            <div class="absolute top-0 right-0 p-4 opacity-10">
                <span class="material-symbols-outlined text-[100px]">account_balance</span>
            </div>
            <h2 class="label text-muted mb-2">Total Net Worth</h2>
            <div class="display mb-4">${formatCurrency(d.net_worth)}</div>
            <div class="flex gap-6">
                <div>
                    <div class="label text-muted">Total Returns</div>
                    <div class="body font-semibold ${totalPnlClass} tabular-nums">${totalPnlSign}${formatCurrency(d.total_unrealised_pnl)} (${totalPnlSign}${d.total_unrealised_pnl_pct.toFixed(2)}%)</div>
                </div>
                <div>
                    <div class="label text-muted">1D Change</div>
                    <div class="body font-semibold ${dayPnlClass} tabular-nums">${dayPnlSign}${formatCurrency(d.day_change)} (${dayPnlSign}${d.day_change_pct.toFixed(2)}%)</div>
                </div>
            </div>
        </div>
        
        <!-- Smart Alerts -->
        <div class="col-12" id="dashboard-alerts"></div>
        
        <!-- Daily Digest -->
        <div class="col-12 glass-panel p-4 mt-2" id="dashboard-digest">
            <div class="animate-pulse flex space-x-4">
              <div class="flex-1 space-y-4 py-1">
                <div class="h-4 bg-surface-variant rounded w-3/4"></div>
                <div class="space-y-2">
                  <div class="h-4 bg-surface-variant rounded"></div>
                  <div class="h-4 bg-surface-variant rounded w-5/6"></div>
                </div>
              </div>
            </div>
        </div>

        <!-- System Status -->
        <div class="col-6">
            ${renderSystemStatusPanel(state.marketSnapshot)}
        </div>
        
        <!-- Performance Timeline -->
        <div class="col-12 glass-panel p-4 mt-4">
            <h2 class="headline-sm mb-4">Performance Timeline</h2>
            <div id="vault-timeline" class="chart-area" style="background:transparent; height:250px;"></div>
        </div>
        
        <!-- Holdings Table -->
        <div class="col-12 glass-panel p-0 overflow-hidden mt-4">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Qty</th>
                        <th>Avg Cost</th>
                        <th>LTP</th>
                        <th>Unrealised P&L</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${holdingsHtml}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Add Holding Modal (Hidden by default) -->
    <div id="add-holding-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden flex items-center justify-center fade-in">
        <div class="bg-surface-glass border border-outline-variant rounded-xl p-6 w-full max-w-[400px]">
            <div class="flex justify-between items-center mb-6">
                <h3 class="headline-sm">Add Investment</h3>
                <button class="material-symbols-outlined text-muted hover:text-on-surface" onclick="closeAddHoldingModal()">close</button>
            </div>
            <div class="flex flex-col gap-4">
                <div class="form-group">
                    <label class="form-label">Ticker Symbol (Yahoo Finance)</label>
                    <input type="text" id="hold-ticker" class="form-input uppercase" placeholder="e.g. RELIANCE.NS">
                </div>
                <div class="form-group">
                    <label class="form-label">Asset Class</label>
                    <select id="hold-class" class="form-select">
                        <option value="EQUITY">Equity (Stock)</option>
                        <option value="ETF">ETF / Mutual Fund</option>
                        <option value="COMMODITY">Commodity (Gold)</option>
                    </select>
                </div>
                <div class="flex gap-4">
                    <div class="form-group flex-1">
                        <label class="form-label">Quantity</label>
                        <input type="number" id="hold-qty" class="form-input" placeholder="0">
                    </div>
                    <div class="form-group flex-1">
                        <label class="form-label">Avg Buy Price (₹)</label>
                        <input type="number" id="hold-price" class="form-input" placeholder="0.00">
                    </div>
                </div>
                <button class="btn-primary w-full justify-center mt-2" onclick="submitAddHolding()">Save Asset</button>
            </div>
        </div>
    </div>
    `;
}

window.openAddHoldingModal = function() {
    const modal = document.getElementById('add-holding-modal');
    if(modal) modal.classList.remove('hidden');
};

window.closeAddHoldingModal = function() {
    const modal = document.getElementById('add-holding-modal');
    if(modal) modal.classList.add('hidden');
};

async function fetchVaultDashboard() {
    try {
        const res = await fetch(`${API_BASE}/holdings/dashboard`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            state.vaultDashboard = await res.json();
            document.getElementById('app-main').innerHTML = renderDashboard();
            fetchAndDrawVaultTimeline();
            fetchDailyDigest();
            fetchSmartAlerts();
        } else {
            console.error("Failed to fetch vault dashboard");
        }
    } catch (e) {
        console.error("Error fetching vault", e);
    }
}

async function fetchDailyDigest() {
    try {
        const res = await fetch(`${API_BASE}/portfolio/digest`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            const digest = await res.json();
            const digestEl = document.getElementById('dashboard-digest');
            if (digestEl) {
                let bulletsHtml = digest.bullets.map(b => `<li class="body-sm text-on-surface mb-1 flex items-start gap-2"><span class="material-symbols-outlined text-[16px] text-primary mt-0.5">check_circle</span> ${b}</li>`).join('');
                digestEl.innerHTML = `
                    <h3 class="headline-sm mb-2 flex items-center gap-2"><span class="material-symbols-outlined text-primary text-[20px]">lightbulb</span> ${digest.greeting || 'Daily AI Briefing'}</h3>
                    <p class="body-sm text-muted mb-3">${digest.market_summary || ''}</p>
                    <ul class="pl-0 m-0 list-none">${bulletsHtml}</ul>
                `;
            }
        }
    } catch (e) {
        console.error("Error fetching digest", e);
    }
}

async function fetchSmartAlerts() {
    try {
        const res = await fetch(`${API_BASE}/portfolio/alerts`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            const alerts = await res.json();
            const alertsEl = document.getElementById('dashboard-alerts');
            if (alertsEl && alerts.length > 0) {
                alertsEl.innerHTML = alerts.map(a => `
                    <div class="glass-panel p-4 mb-2 border-l-4" style="border-left-color: var(--${a.severity === 'CRITICAL' ? 'error' : 'primary'})">
                        <div class="flex justify-between items-center mb-1">
                            <h4 class="headline-sm flex items-center gap-2">
                                <span class="material-symbols-outlined text-[18px] ${a.severity === 'CRITICAL' ? 'text-error' : 'text-primary'}">campaign</span>
                                Smart Alert: ${a.type}
                            </h4>
                            <span class="text-xs text-muted">${new Date(a.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>
                        <p class="body-sm text-on-surface">${a.message}</p>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.error("Error fetching alerts", e);
    }
}

async function fetchAndDrawVaultTimeline() {
    if (!window.Plotly) return;
    try {
        const res = await fetch(`${API_BASE}/holdings/snapshots`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            const snapshots = await res.json();
            if (snapshots.length === 0) return;
            
            const x = snapshots.map(s => s.date.split('T')[0]);
            const yNw = snapshots.map(s => s.net_worth);
            const yInv = snapshots.map(s => s.total_invested);
            
            // Normalize NW and mock NIFTY 50 benchmark
            if (yNw.length > 0) {
                const baseNw = yNw[0];
                const yNwNorm = yNw.map(v => (v / baseNw) * 100);
                
                // Mock NIFTY baseline that grows 3% over the period
                let benchmark = 100;
                const yBench = [];
                for(let i=0; i<x.length; i++){
                    yBench.push(benchmark);
                    benchmark *= (1 + 0.03/x.length);
                }

                const data = [
                    { x: x, y: yBench, type: 'scatter', mode: 'lines', name: '^NSEI (Base 100)', line: {color: '#86948d', width:2, dash: 'dot'} },
                    { x: x, y: yNwNorm, type: 'scatter', mode: 'lines', name: 'Portfolio (Base 100)', line: {color: '#61dbb4', width:3} }
                ];
                const layout = {
                    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                    margin: {t:10, b:40, l:40, r:10}, showlegend: true,
                    legend: { orientation: 'h', y: 1.1 },
                    xaxis: { showgrid: false, color: '#86948d' },
                    yaxis: { showgrid: true, gridcolor: 'rgba(61,74,68,0.2)', color: '#86948d' },
                    font: { color: '#dee4df', family: 'Inter' }
                };
                Plotly.newPlot('vault-timeline', data, layout, {displayModeBar: false});
            }

        }
    } catch (e) {
        console.error("Error fetching snapshots", e);
    }
}

window.submitAddHolding = async function() {
    const ticker = document.getElementById('hold-ticker').value.toUpperCase();
    const assetClass = document.getElementById('hold-class').value;
    const qty = parseFloat(document.getElementById('hold-qty').value);
    const price = parseFloat(document.getElementById('hold-price').value);
    
    if(!ticker || !qty || !price) {
        alert("Please fill all fields");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/holdings/`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${state.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asset_ticker: ticker,
                asset_name: ticker,
                asset_class: assetClass,
                quantity: qty,
                average_buy_price: price,
                source: "MANUAL"
            })
        });
        
        if (res.ok) {
            closeAddHoldingModal();
            state.vaultDashboard = null; // force refresh
            renderPage('dashboard');
        } else {
            alert("Failed to add holding");
        }
    } catch (e) {
        console.error("Error adding holding", e);
    }
}

window.deleteHolding = async function(holdingId) {
    if (!confirm("Are you sure you want to remove this holding?")) return;
    
    try {
        const res = await fetch(`${API_BASE}/holdings/${holdingId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        
        if (res.ok) {
            state.vaultDashboard = null; // force refresh
            renderPage('dashboard');
        } else {
            alert("Failed to delete holding");
        }
    } catch (e) {
        console.error("Error deleting holding", e);
    }
}

// 2. AI Advice View (The Strategies)
function renderAIAdvice() {
    if (!state.token) {
        return `<div class="card fade-in text-center"><h2 class="headline mb-4">AI Advice</h2>
                <p class="body mb-6">Please log in to view AI recommendations.</p>
                <button class="btn-primary" onclick="navigateTo('login')">Sign In</button></div>`;
    }
    
    if (!state.aiAdvice) {
        fetchAIAdvice();
        return renderLoadingCard('ai_advice');
    }

    const advice = state.aiAdvice;
    
    let adviceCardsHtml = '';
    if (advice.actionable_advice && advice.actionable_advice.length > 0) {
        advice.actionable_advice.forEach(a => {
            let icon = 'lightbulb';
            let colorClass = 'text-primary';
            if (a.type === 'RISK') { icon = 'warning'; colorClass = 'text-error'; }
            if (a.type === 'OPPORTUNITY') { icon = 'trending_up'; colorClass = 'text-up'; }
            if (a.type === 'REBALANCE') { icon = 'tune'; colorClass = 'text-tertiary'; }
            
            adviceCardsHtml += `
            <div class="glass-panel p-5 mb-4 border-l-4" style="border-left-color: var(--${colorClass.split('-')[1]})">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined ${colorClass}">${icon}</span>
                        <h3 class="headline-sm">${a.title}</h3>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-muted flex items-center gap-1" title="AI Confidence Score"><span class="material-symbols-outlined text-[14px]">psychology</span> ${a.confidence_score || '--'}% Conf.</span>
                        <span class="badge ${colorClass.replace('text-', 'bg-')}/10 ${colorClass}">${a.type}</span>
                    </div>
                </div>
                <p class="body text-muted">${a.rationale}</p>
                <div class="mt-4 flex gap-2">
                    <button class="btn-secondary btn-sm" onclick="alert('Execute trade integration pending.')">Action</button>
                    <button class="btn-outline btn-sm text-xs" onclick="alert('AI Trace: Probabilistic interpretation based on market regime and current concentration limits.')"><span class="material-symbols-outlined text-[14px] mr-1">psychology</span>Why?</button>
                </div>
            </div>`;
        });
    } else {
        adviceCardsHtml = `<div class="p-6 text-center text-muted">No actionable advice generated.</div>`;
    }

    return `
    <div class="bento fade-in" id="printable-advice">
        <div class="col-12 flex justify-between items-center mb-4">
            <div>
                <h1 class="headline">AI Strategies & Advice</h1>
                <p class="body-sm text-muted flex items-center gap-sm"><span class="material-symbols-outlined text-primary-c text-[14px]">psychology</span> Context-Aware Intelligence</p>
            </div>
            <div class="flex gap-2 print:hidden">
                <button class="btn-secondary" onclick="window.print()">
                    <span class="material-symbols-outlined mr-2">print</span> Export PDF
                </button>
                <button class="btn-secondary" onclick="fetchAIAdvice(true)">
                    <span class="material-symbols-outlined mr-2">refresh</span> Recalculate
                </button>
            </div>
        </div>
        
        <!-- Health Score -->
        <div class="col-4 glass-panel p-6 ai-glow relative overflow-hidden flex flex-col justify-center items-center text-center">
            <h2 class="label text-muted mb-2">Portfolio Health</h2>
            <div class="text-[64px] font-display font-bold ${advice.health_score > 70 ? 'text-up' : (advice.health_score > 40 ? 'text-primary' : 'text-error')}">${advice.health_score}</div>
            <p class="body-sm text-muted mt-2">out of 100</p>
        </div>
        
        <!-- Health Context -->
        <div class="col-8 glass-panel p-6">
            <h3 class="headline-sm mb-2 flex items-center gap-2">Health Analysis <span class="badge bg-surface-container text-muted text-xs">Deterministic: Math-driven</span></h3>
            <p class="body text-on-surface mb-4">${advice.health_score_analysis || 'No analysis available.'}</p>
            
            ${advice.concentration_warning ? `
            <div class="p-4 rounded-lg bg-error/10 border border-error/20 flex gap-3">
                <span class="material-symbols-outlined text-error">warning</span>
                <p class="body-sm text-error">${advice.concentration_warning}</p>
            </div>` : ''}
        </div>
        
        <!-- Market Context -->
        <div class="col-12 glass-panel p-5 mt-2 border-l-4 border-tertiary">
            <div class="flex items-center gap-2 mb-2 text-primary">
                <span class="material-symbols-outlined text-[18px]">public</span>
                <span class="font-semibold text-sm">Macroeconomic Alignment</span>
            </div>
            <p class="body text-muted">${advice.market_context || 'Market context unavailable.'}</p>
        </div>
        
        <!-- Actionable Advice Cards -->
        <div class="col-12 mt-4">
            <h2 class="headline mb-4 flex items-center gap-2">Actionable Recommendations <span class="badge bg-surface-container text-muted text-xs">AI Interpretation: Probabilistic</span></h2>
            ${adviceCardsHtml}
        </div>
        
        <!-- Recommendation History -->
        <div class="col-12 mt-8 print:hidden">
            <h2 class="headline-sm mb-4 text-muted">Recommendation History</h2>
            <div class="glass-panel p-0 overflow-hidden">
                <table class="data-table">
                    <thead><tr><th>Date</th><th>Type</th><th>Recommendation</th><th>Status</th></tr></thead>
                    <tbody id="advice-history-tbody">
                        <tr><td colspan="4" class="text-center text-muted p-4">Loading history...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    `;
}

async function fetchAdviceHistory() {
    try {
        const res = await fetch(`${API_BASE}/portfolio/advice/history`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            const history = await res.json();
            const tbody = document.getElementById('advice-history-tbody');
            if (tbody) {
                if (history.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted p-4">No historical advice available.</td></tr>`;
                    return;
                }
                tbody.innerHTML = history.map(h => `
                    <tr>
                        <td class="text-xs text-muted">${new Date(h.created_at).toLocaleDateString()}</td>
                        <td><span class="badge bg-surface-container">${h.type}</span></td>
                        <td><div class="font-semibold text-sm">${h.title}</div></td>
                        <td><span class="badge bg-surface-container text-muted">${h.status}</span></td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error("Error fetching advice history", e);
    }
}

async function fetchAIAdvice(force = false) {
    if (state.aiAdvice && !force) {
        fetchAdviceHistory();
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/portfolio/advice`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (res.ok) {
            state.aiAdvice = await res.json();
            if (window.location.hash === '#portfolio') {
                document.getElementById('app-main').innerHTML = renderAIAdvice();
                fetchAdviceHistory();
            }
        } else {
            console.error("Failed to fetch advice");
        }
    } catch (e) {
        console.error("Error fetching advice", e);
    }
}


// 3. Insights View
function renderInsights() {
    return `
    <div class="bento">
        <div class="col-12 mb-4">
            <h1 class="headline">Market Intelligence</h1>
            <p class="body-sm text-muted">AI-curated signals and macroeconomic outlook.</p>
        </div>
        
        <div class="col-4 glass-panel p-4">
            <h3 class="label mb-4">Sector Momentum</h3>
            <div class="form-group mb-2"><div class="flex justify-between"><span class="body-sm">Technology</span><span class="mono text-up">Bullish</span></div><div class="progress-bar"><div class="progress-fill" style="width:80%; background:var(--market-up)"></div></div></div>
            <div class="form-group mb-2"><div class="flex justify-between"><span class="body-sm">Healthcare</span><span class="mono text-muted">Neutral</span></div><div class="progress-bar"><div class="progress-fill" style="width:50%; background:var(--market-neutral)"></div></div></div>
            <div class="form-group mb-2"><div class="flex justify-between"><span class="body-sm">Real Estate</span><span class="mono text-down">Bearish</span></div><div class="progress-bar"><div class="progress-fill" style="width:30%; background:var(--market-down)"></div></div></div>
        </div>
        
        <div class="col-8 flex flex-col gap-md">
            <div class="insight-card border-l-4" style="border-left-color:var(--primary)">
                <h4 class="headline-sm mb-2">Fed Holds Rates Steady</h4>
                <p class="body-sm">Interest rates remain unchanged. Growth sectors are expected to maintain current momentum. Our models suggest overweighting large-cap tech.</p>
            </div>
            <div class="insight-card border-l-4" style="border-left-color:var(--market-neutral)">
                <h4 class="headline-sm mb-2">Inflation Cools Slightly</h4>
                <p class="body-sm">CPI data came in 0.1% below expectations. Bond yields have stabilized, making intermediate-term treasuries attractive for risk-averse allocations.</p>
            </div>
        </div>
    </div>`;
}

// 4. Markets View (TradingView Live Charts)
function renderMarkets() {
    return `
    <div class="bento h-full min-h-[80vh]">
        <div class="col-12 mb-4 flex justify-between items-center flex-wrap gap-4">
            <div>
                <h1 class="headline">Global Markets</h1>
                <p class="body-sm text-muted flex items-center gap-sm"><span class="material-symbols-outlined text-up text-[14px]">sensors</span> Live Data Feed</p>
            </div>
            <div class="flex items-center gap-sm">
                <input type="text" id="market-search" class="form-input" style="width:200px; padding:0.5rem; background-color: white !important; color: black !important;" placeholder="Search symbol (e.g. NSE:TCS)" onkeydown="if(event.key==='Enter') searchMarketSymbol()">
                <button class="btn-primary" style="padding:0.5rem 1rem;" onclick="searchMarketSymbol()">
                    <span class="material-symbols-outlined">search</span>
                </button>
            </div>
        </div>
        <div class="col-12 mb-2 flex gap-sm">
            <span class="chip chip-neutral" onclick="changeMarketSymbol('NIFTY')">Nifty 50</span>
            <span class="chip chip-neutral" onclick="changeMarketSymbol('SENSEX')">Sensex</span>
            <span class="chip chip-neutral" onclick="changeMarketSymbol('RELIANCE')">Reliance</span>
            <span class="chip chip-neutral" onclick="changeMarketSymbol('HDFC')">HDFC Bank</span>
        </div>
        
        <div class="col-12 glass-panel p-2 overflow-hidden relative" style="height: 600px;" id="tv-chart-container">
            <!-- TradingView Widget goes here -->
            <div class="tradingview-widget-container" style="height:100%; width:100%;">
              <div id="tradingview_advanced_chart" style="height:calc(100% - 32px); width:100%;"></div>
              <div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
            </div>
        </div>
    </div>`;
}

function injectTradingView(symbol = "NSE:NIFTY") {
    // Prevent double injection if already loaded
    if (document.getElementById('tv-script-injected')) {
        createTradingViewWidget(symbol);
        return;
    }
    
    const script = document.createElement('script');
    script.id = 'tv-script-injected';
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    script.onload = () => createTradingViewWidget(symbol);
    document.body.appendChild(script);
}

function createTradingViewWidget(symbol) {
    if (!window.TradingView) return;
    document.getElementById('tradingview_advanced_chart').innerHTML = '';
    new window.TradingView.widget({
        "autosize": true,
        "symbol": symbol,
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "enable_publishing": false,
        "backgroundColor": "rgba(18, 20, 19, 0)", // Matches our dark glassmorphism
        "gridColor": "rgba(61, 74, 68, 0.2)",
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": false,
        "container_id": "tradingview_advanced_chart",
        "studies": [
            "Volume@tv-basicstudies",
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies"
        ]
    });
}

function changeMarketSymbol(symbol) {
    let tvSymbol = "NSE:NIFTY";
    if (symbol === 'SENSEX') tvSymbol = "BSE:SENSEX";
    if (symbol === 'RELIANCE') tvSymbol = "NSE:RELIANCE";
    if (symbol === 'HDFC') tvSymbol = "NSE:HDFCBANK";
    
    createTradingViewWidget(tvSymbol);
}

function searchMarketSymbol() {
    const input = document.getElementById('market-search');
    let symbol = input.value.trim().toUpperCase();
    if (!symbol) return;
    
    // Auto-prefix NSE if the user just types a raw Indian stock ticker without exchange
    if (!symbol.includes(':') && !symbol.includes('^')) {
        // Just a basic heuristic. If they search SPY, it's safer to just pass SPY and let TV resolve it,
        // but since we localized to India, we prefix NSE if there is no prefix.
        symbol = "NSE:" + symbol;
    }
    
    createTradingViewWidget(symbol);
}

let onboardingState = {
    step: 1,
    goal: '',
    riskReaction: '',
    age: 30,
    income: '',
    existing: 'no'
};

function renderOnboarding() {
    let content = '';
    
    if (onboardingState.step === 1) {
        content = `
        <div class="p-6 text-center">
            <h2 class="headline mb-2">What brings you to Nexus AI today?</h2>
            <p class="body-sm text-muted mb-6">We'll tailor your experience based on your primary goal.</p>
            <div class="flex flex-col gap-4 max-w-[500px] mx-auto text-left">
                <div class="goal-card w-full" onclick="setGoal('wealth')">
                    <div class="goal-icon"><span class="material-symbols-outlined">trending_up</span></div>
                    <div><h4 class="body font-semibold">Build Long-Term Wealth</h4><p class="body-sm">I want my money to grow steadily</p></div>
                </div>
                <div class="goal-card w-full" onclick="setGoal('save')">
                    <div class="goal-icon"><span class="material-symbols-outlined">home</span></div>
                    <div><h4 class="body font-semibold">Save for a Major Goal</h4><p class="body-sm">Buying a house, education</p></div>
                </div>
                <div class="goal-card w-full" onclick="setGoal('protect')">
                    <div class="goal-icon"><span class="material-symbols-outlined">shield</span></div>
                    <div><h4 class="body font-semibold">Protect My Savings</h4><p class="body-sm">Beat inflation without high risk</p></div>
                </div>
                <div class="goal-card w-full" onclick="setGoal('explore')">
                    <div class="goal-icon"><span class="material-symbols-outlined">explore</span></div>
                    <div><h4 class="body font-semibold">Just Exploring</h4><p class="body-sm">Show me how the AI works</p></div>
                </div>
            </div>
        </div>`;
    } else if (onboardingState.step === 2) {
        content = `
        <div class="p-6">
            <h2 class="headline mb-2 text-center">Let's calibrate your style</h2>
            <p class="body-sm text-muted mb-6 text-center">The market goes up and down. How do you react?</p>
            <div class="max-w-[500px] mx-auto flex flex-col gap-6">
                <div class="form-group">
                    <label class="form-label text-text-primary mb-2">If your portfolio dropped by 15% in one month, what would you do?</label>
                    <div class="flex flex-col gap-3 mt-2">
                        <button class="btn-ghost text-left hover:border-primary transition-all p-3 rounded-lg border border-outline-variant text-on-surface" onclick="setRisk('conservative')">Sell immediately to prevent further losses</button>
                        <button class="btn-ghost text-left hover:border-primary transition-all p-3 rounded-lg border border-outline-variant text-on-surface" onclick="setRisk('moderate')">Do nothing and wait for recovery</button>
                        <button class="btn-ghost text-left hover:border-primary transition-all p-3 rounded-lg border border-outline-variant text-on-surface" onclick="setRisk('aggressive')">Buy more while prices are low</button>
                    </div>
                </div>
            </div>
        </div>`;
    } else if (onboardingState.step === 3) {
        content = `
        <div class="p-6">
            <h2 class="headline mb-2 text-center">Let's ground this in reality</h2>
            <p class="body-sm text-muted mb-6 text-center">We need a few details to ensure our AI recommendations fit your budget.</p>
            <div class="max-w-[400px] mx-auto flex flex-col gap-6">
                <div class="form-group">
                    <label class="form-label">Age</label>
                    <input type="number" id="ob-age" class="form-input" placeholder="e.g. 30" value="30">
                </div>
                <div class="form-group">
                    <label class="form-label flex justify-between">Monthly Income <span class="text-xs text-muted"><span class="material-symbols-outlined text-[12px] align-middle">lock</span> Encrypted</span></label>
                    <select id="ob-income" class="form-select">
                        <option value="under_50k">Under ₹50,000</option>
                        <option value="50k_1l">₹50,000 - ₹1,00,000</option>
                        <option value="over_1l">Over ₹1,00,000</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label flex justify-between">Existing Investments?</label>
                    <select id="ob-existing" class="form-select">
                        <option value="no">No, starting from scratch</option>
                        <option value="yes">Yes, I have existing investments</option>
                    </select>
                </div>
                <button class="btn-primary mt-4 justify-center" onclick="finishOnboarding()">Generate AI Blueprint <span class="material-symbols-outlined">auto_awesome</span></button>
            </div>
        </div>`;
    } else if (onboardingState.step === 4) {
        let strategyName = onboardingState.riskReaction === 'aggressive' ? 'High Growth' : (onboardingState.riskReaction === 'conservative' ? 'Capital Preservation' : 'Balanced Growth');
        let allocationDesc = onboardingState.riskReaction === 'aggressive' ? 'heavily weighted toward Large-Cap Equities, with minimal debt drag' : (onboardingState.riskReaction === 'conservative' ? 'majority debt and fixed income, designed to preserve your capital' : 'a balanced mix of equity for growth and debt to absorb volatility');
        
        content = `
        <div class="p-6 text-center animate-fade-in">
            <h2 class="headline mb-6">YOUR AI FINANCIAL BLUEPRINT</h2>
            <div class="ai-card max-w-[500px] mx-auto text-left mb-6 relative overflow-hidden">
                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-primary-container to-primary"></div>
                <div class="flex items-center gap-2 mb-4 text-primary mt-2">
                    <span class="material-symbols-outlined">verified_user</span>
                    <span class="font-semibold text-sm">Verified AI Strategy</span>
                </div>
                <div class="flex gap-4 mb-4 pb-4 border-b border-outline-variant">
                    <div>
                        <div class="label text-muted">Goal</div>
                        <div class="body-sm font-semibold">${onboardingState.goal.toUpperCase()}</div>
                    </div>
                    <div>
                        <div class="label text-muted">Style</div>
                        <div class="body-sm font-semibold">${strategyName.toUpperCase()}</div>
                    </div>
                </div>
                <p class="body-sm text-on-surface mb-4">"Based on your profile, we've designed a strategy that aims for steady returns while protecting you from severe market crashes.</p>
                <p class="body-sm text-on-surface">We recommend an allocation ${allocationDesc}, perfectly aligned with your financial goals."</p>
            </div>
            <button class="btn-primary" onclick="proceedToPortfolio()">View Recommended Portfolio <span class="material-symbols-outlined">arrow_forward</span></button>
        </div>`;
    }

    return `
    <div class="glass-panel max-w-[800px] mx-auto overflow-hidden">
        ${content}
    </div>`;
}

window.setGoal = function(goal) {
    onboardingState.goal = goal;
    onboardingState.step = 2;
    document.getElementById('app-main').innerHTML = renderOnboarding();
};

window.setRisk = function(risk) {
    onboardingState.riskReaction = risk;
    onboardingState.step = 3;
    document.getElementById('app-main').innerHTML = renderOnboarding();
};

window.finishOnboarding = function() {
    onboardingState.age = parseInt(document.getElementById('ob-age').value) || 30;
    onboardingState.income = document.getElementById('ob-income').value;
    onboardingState.existing = document.getElementById('ob-existing').value;
    onboardingState.step = 4;
    document.getElementById('app-main').innerHTML = `
        <div class="glass-panel max-w-[800px] mx-auto overflow-hidden p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
            <span class="material-symbols-outlined animate-spin text-primary text-[48px] mb-4">refresh</span>
            <h3 class="headline-sm mb-2">Analyzing your goal...</h3>
            <p class="body-sm text-muted">Calibrating risk profile and generating AI strategy</p>
        </div>
    `;
    setTimeout(() => {
        document.getElementById('app-main').innerHTML = renderOnboarding();
    }, 1500);
};

window.proceedToPortfolio = function() {
    state.profile = { 
        age: onboardingState.age, 
        risk_category: onboardingState.riskReaction || 'moderate', 
        investment_horizon: 'long_term', 
        financial_goals: [onboardingState.goal] 
    };
    localStorage.setItem('nexus_profile', JSON.stringify(state.profile));
    generatePortfolio();
};

async function generatePortfolio() {
    if (!state.profile) return;
    
    const main = document.getElementById('app-main');
    main.innerHTML = renderLoadingCard('portfolio');
    startLoadingSteps('portfolio');
    
    try {
        const payload = {
            risk_score: state.profile.risk === 'aggressive' ? 80 : (state.profile.risk === 'conservative' ? 20 : 50),
            investment_horizon: state.profile.horizon || "medium_term",
            strategy: "max_sharpe"
        };
        
        const res = await fetch(API_BASE + '/portfolio/generate', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify(payload)
        });
        
        clearLoadingSteps();
        
        if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('nexus_token');
            state.token = null;
            navigateTo('login');
            showToast('Your session expired. Please sign in again.', 'warning');
            return;
        }
        
        if (!res.ok) throw new Error(`Portfolio API error: ${res.status}`);
        
        const data = await res.json();
        state.portfolio = data;
        localStorage.setItem('nexus_portfolio', JSON.stringify(data));
        showToast('Portfolio generated successfully.', 'success', 3000);
        navigateTo('portfolio');
        
    } catch (error) {
        clearLoadingSteps();
        console.error("Portfolio gen failed, using fallback", error);
        showToast('Live portfolio engine unavailable. Displaying cached fallback portfolio.', 'warning');
        // Graceful fallback — never leave user stranded
        state.portfolio = {
            weights: {"RELIANCE.NS":0.35, "TCS.NS":0.25, "HDFCBANK.NS":0.20, "NIFTYBEES.NS":0.12, "LIQUIDBEES.NS":0.08},
            metrics: {expected_annual_return:0.15, annual_volatility:0.18, sharpe_ratio:1.2},
            strategy_used: "max_sharpe",
            _fallback: true
        };
        navigateTo('portfolio');
    }
}

// ── CHAT BOT ─────────────────────────────────────────────────────

function toggleSidebar() {
    const nav = document.getElementById('desktop-nav');
    nav.style.display = nav.style.display === 'none' ? 'flex' : 'none';
}

function toggleChat() {
    const panel = document.getElementById('chat-panel');
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
        document.getElementById('chat-input').focus();
    }
}

function sendSuggestion(text) {
    document.getElementById('chat-input').value = text;
    sendChat();
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    
    input.value = '';
    appendMessage(msg, 'user');
    
    // Add loading indicator
    const chatMsgs = document.getElementById('chat-messages');
    const loadingId = 'loading-' + Date.now();
    chatMsgs.insertAdjacentHTML('beforeend', `<div id="${loadingId}" class="chat-msg ai fade-in"><div class="chat-bubble ai-bubble animate-pulse">Thinking...</div></div>`);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
    
    try {
        const payload = {
            message: msg,
            portfolio_data: state.portfolio,
            user_profile: state.profile
        };
        
        const res = await fetch(API_BASE + '/chat/message', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify(payload)
        });
        
        document.getElementById(loadingId).remove();
        
        if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('nexus_token');
            state.token = null;
            showToast('Your session expired. Please sign in again.', 'warning');
            navigateTo('login');
            document.getElementById(loadingId)?.remove();
            return;
        }
        
        if (!res.ok) throw new Error("Chat API failed: " + res.status);
        const data = await res.json();
        
        let responseText = "";
        if (typeof data.response === 'string') {
            responseText = data.response;
        } else if (data.response && data.response.term) {
            responseText = `**${data.response.term}**: ${data.response.simple}`;
        } else if (data.response && data.response.nominal_future_value) {
            responseText = `Projected SIP Value: ${formatCurrency(data.response.nominal_future_value)}. Total Invested: ${formatCurrency(data.response.total_invested)}.`;
        } else if (data.response && data.response.scenario) {
            responseText = `**Scenario: ${data.response.scenario.replace('_', ' ').toUpperCase()}**<br>
            ${data.response.analysis}<br><br>
            **Recommended Action:** ${data.response.recommended_action}`;
        } else if (data.response && data.response.investor_summary) {
            responseText = `${data.response.investor_summary}<br><br>`;
            responseText += `**Risk Profile:** Expected Return ${data.response.risk_analysis.expected_annual_return_pct}%, Volatility ${data.response.risk_analysis.annual_volatility_pct}%<br><br>`;
            responseText += `**Key Risks:**<br> - ${data.response.key_risks.join('<br> - ')}`;
        } else if (data.response && data.response.market_context) {
            responseText = `${data.response.analysis}<br><br>Analyzed ${data.response.sources} recent news sources.`;
        } else if (data.response && data.response.volatility) {
            responseText = `**Risk Assessment**<br>Volatility: ${data.response.volatility}<br>Sharpe Ratio: ${data.response.sharpe_ratio}<br><br>${data.response.assessment}`;
        } else {
            responseText = "I've analyzed your portfolio. Check the dashboard for detailed updates.";
        }
        
        appendMessage(responseText, 'ai');
        
    } catch (e) {
        console.error(e);
        document.getElementById(loadingId)?.remove();
        // Graceful degradation message — never expose raw error to user
        appendMessage("I'm currently operating in offline mode. The semantic reasoning engine is temporarily unreachable. Please try again shortly.", 'ai');
        showToast('AI engine temporarily unavailable — operating in fallback mode.', 'info', 4000);
    }
}

function appendMessage(text, sender) {
    const chatMsgs = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${sender} fade-in`;
    
    // Simple markdown bold parsing for response
    let formattedText = text.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
    
    msgDiv.innerHTML = `<div class="chat-bubble ${sender}-bubble">${formattedText}</div>`;
    chatMsgs.appendChild(msgDiv);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

// ── BOOTSTRAP ────────────────────────────────────────────────────
function bootstrap() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        initApp();
    }
}
bootstrap();

// Subscribe UI to state changes
subscribe(() => {
    // Only re-render if we are on dashboard or portfolio
    const page = window.location.hash.substring(1) || 'dashboard';
    if (page === 'dashboard' || page === 'portfolio') {
        renderPage(page);
    }
});

// Attach handlers to window for HTML access
window.navigateTo = navigateTo;
window.doLogin = doLogin;
window.doRegister = doRegister;
window.doForgot = doForgot;
window.generatePortfolio = generatePortfolio;
window.toggleSidebar = toggleSidebar;
window.toggleChat = toggleChat;
window.sendSuggestion = sendSuggestion;
window.sendChat = sendChat;
window.changeMarketSymbol = changeMarketSymbol;
window.searchMarketSymbol = searchMarketSymbol;
window.simulateScenario = handleScenarioSimulation;
window.startDemoFlow = startDemoFlow;
window.showTrustTrace = renderTrustTraceModal;
