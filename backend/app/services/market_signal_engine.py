import pandas as pd
import numpy as np

def compute_rsi(prices: pd.Series, window: int = 14) -> float:
    """Compute Relative Strength Index (Momentum)"""
    if len(prices) < window:
        return 50.0
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return val if not pd.isna(val) else 50.0

def compute_sma_trend(prices: pd.Series, short_win: int = 50, long_win: int = 200) -> str:
    """Compute 50/200 SMA crossover trend."""
    if len(prices) < long_win:
        # Fallback to shorter windows if data is limited
        if len(prices) > 50:
            short_win = 20
            long_win = 50
        else:
            return "Neutral"
            
    short_sma = prices.rolling(window=short_win).mean().iloc[-1]
    long_sma = prices.rolling(window=long_win).mean().iloc[-1]
    
    if short_sma > long_sma * 1.02:
        return "Bullish"
    elif short_sma < long_sma * 0.98:
        return "Bearish"
    return "Neutral"

def compute_volatility(prices: pd.Series, window: int = 20) -> str:
    """Compute annualized volatility and categorize risk."""
    if len(prices) < window:
        return "Moderate"
    returns = prices.pct_change()
    vol = returns.rolling(window=window).std().iloc[-1] * np.sqrt(252)
    
    if vol > 0.25:
        return "High"
    elif vol < 0.12:
        return "Low"
    return "Moderate"

def compute_inflation_delta(current_cpi: float, prev_cpi: float) -> str:
    """Determine Macro Regime from inflation delta."""
    if current_cpi > prev_cpi * 1.002:
        return "Rising"
    elif current_cpi < prev_cpi * 0.998:
        return "Falling"
    return "Stable"

def compute_bond_yield_trend(yields: pd.Series) -> str:
    """Determine defensive pressure based on TLT/Bond yields."""
    if len(yields) < 20:
        return "Stable"
    # Simple proxy: if TLT price goes down, yields go up.
    # So if TLT is Bearish trend, yields are Rising (Defensive pressure).
    trend = compute_sma_trend(yields, 20, 50)
    if trend == "Bullish":
        return "Falling" # Yields falling, TLT rising
    elif trend == "Bearish":
        return "Rising"  # Yields rising, TLT falling
    return "Stable"

def compute_sector_relative_strength(sector_prices: pd.Series, benchmark_prices: pd.Series) -> float:
    """Compute relative strength of a sector vs benchmark (e.g. QQQ vs SPY)"""
    if len(sector_prices) < 20 or len(benchmark_prices) < 20:
        return 0.5
        
    sector_ret = (sector_prices.iloc[-1] - sector_prices.iloc[-20]) / sector_prices.iloc[-20]
    bench_ret = (benchmark_prices.iloc[-1] - benchmark_prices.iloc[-20]) / benchmark_prices.iloc[-20]
    
    # Simple score between 0 and 1 representing relative momentum
    diff = sector_ret - bench_ret
    score = 0.5 + (diff * 2) # Arbitrary scaling for illustration
    return max(0.0, min(1.0, float(score)))
