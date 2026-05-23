"""
Technical Indicators Service.
Computes RSI, SMA, EMA, MACD, Bollinger Bands, Volatility,
Beta, Sharpe Ratio, and Max Drawdown from price data.
All indicators from the implementation plan §2.3.
"""

import numpy as np
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Computes all technical indicators from a pandas DataFrame
    with columns: ['close'] indexed by date.
    """

    def __init__(self, prices: pd.Series, risk_free_rate: float = 0.05):
        """
        Args:
            prices: pd.Series of closing prices indexed by date.
            risk_free_rate: Annual risk-free rate (default 5%).
        """
        if prices.empty:
            raise ValueError("Cannot compute indicators on empty price series.")

        self.prices = prices.sort_index().astype(float)
        self.returns = self.prices.pct_change().dropna()
        self.rf_daily = risk_free_rate / 252

    # ── RSI (14-day) ──────────────────────────────────────────
    def rsi(self, period: int = 14) -> Optional[float]:
        """Relative Strength Index. Returns None if insufficient data."""
        if len(self.prices) < period + 1:
            return None
        delta = self.prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        latest = rsi.iloc[-1]
        return round(float(latest), 2) if not np.isnan(latest) else None

    # ── Simple Moving Averages ────────────────────────────────
    def sma(self, period: int) -> Optional[float]:
        """Simple Moving Average for the given period."""
        if len(self.prices) < period:
            return None
        val = self.prices.rolling(window=period).mean().iloc[-1]
        return round(float(val), 4) if not np.isnan(val) else None

    # ── Exponential Moving Averages ───────────────────────────
    def ema(self, period: int) -> Optional[float]:
        """Exponential Moving Average for the given period."""
        if len(self.prices) < period:
            return None
        val = self.prices.ewm(span=period, adjust=False).mean().iloc[-1]
        return round(float(val), 4) if not np.isnan(val) else None

    # ── MACD ──────────────────────────────────────────────────
    def macd(self) -> dict:
        """MACD line, Signal line, and Histogram."""
        if len(self.prices) < 26:
            return {"macd": None, "signal": None, "histogram": None}

        ema12 = self.prices.ewm(span=12, adjust=False).mean()
        ema26 = self.prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": round(float(macd_line.iloc[-1]), 4),
            "signal": round(float(signal_line.iloc[-1]), 4),
            "histogram": round(float(histogram.iloc[-1]), 4),
        }

    # ── Bollinger Bands ───────────────────────────────────────
    def bollinger_bands(self, period: int = 20, num_std: float = 2.0) -> dict:
        """Upper and Lower Bollinger Bands."""
        if len(self.prices) < period:
            return {"upper": None, "lower": None, "middle": None}

        sma = self.prices.rolling(window=period).mean()
        std = self.prices.rolling(window=period).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)

        return {
            "upper": round(float(upper.iloc[-1]), 4) if not np.isnan(upper.iloc[-1]) else None,
            "lower": round(float(lower.iloc[-1]), 4) if not np.isnan(lower.iloc[-1]) else None,
            "middle": round(float(sma.iloc[-1]), 4) if not np.isnan(sma.iloc[-1]) else None,
        }

    # ── 30-Day Volatility ─────────────────────────────────────
    def volatility_30d(self) -> Optional[float]:
        """Annualized 30-day rolling volatility."""
        if len(self.returns) < 30:
            return None
        vol = self.returns.iloc[-30:].std() * np.sqrt(252)
        return round(float(vol), 4) if not np.isnan(vol) else None

    # ── Beta ──────────────────────────────────────────────────
    def beta(self, benchmark_returns: pd.Series) -> Optional[float]:
        """
        Beta = Cov(asset, benchmark) / Var(benchmark).
        Requires aligned benchmark returns series.
        """
        if len(self.returns) < 30 or len(benchmark_returns) < 30:
            return None

        # Align on common dates
        aligned = pd.DataFrame({
            "asset": self.returns,
            "benchmark": benchmark_returns,
        }).dropna()

        if len(aligned) < 30:
            return None

        cov = aligned["asset"].cov(aligned["benchmark"])
        var = aligned["benchmark"].var()
        if var == 0:
            return None

        return round(float(cov / var), 4)

    # ── Sharpe Ratio ──────────────────────────────────────────
    def sharpe_ratio(self) -> Optional[float]:
        """Annualized Sharpe Ratio = (mean_return - Rf) / std_return * sqrt(252)."""
        if len(self.returns) < 30:
            return None
        excess = self.returns - self.rf_daily
        mean_excess = excess.mean()
        std_excess = excess.std()
        if std_excess == 0:
            return None
        sharpe = (mean_excess / std_excess) * np.sqrt(252)
        return round(float(sharpe), 4)

    # ── Max Drawdown ──────────────────────────────────────────
    def max_drawdown(self) -> Optional[float]:
        """Maximum peak-to-trough decline as a percentage."""
        if len(self.prices) < 2:
            return None
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        mdd = drawdown.min()
        return round(float(mdd) * 100, 2) if not np.isnan(mdd) else None

    # ── Compute All ───────────────────────────────────────────
    def compute_all(self, benchmark_returns: Optional[pd.Series] = None) -> dict:
        """Compute all indicators and return as a flat dict."""
        macd_data = self.macd()
        bb_data = self.bollinger_bands()

        result = {
            "rsi_14": self.rsi(14),
            "sma_50": self.sma(50),
            "sma_200": self.sma(200),
            "ema_12": self.ema(12),
            "ema_26": self.ema(26),
            "macd": macd_data["macd"],
            "macd_signal": macd_data["signal"],
            "bollinger_upper": bb_data["upper"],
            "bollinger_lower": bb_data["lower"],
            "volatility_30d": self.volatility_30d(),
            "sharpe_ratio": self.sharpe_ratio(),
            "max_drawdown": self.max_drawdown(),
            "beta": self.beta(benchmark_returns) if benchmark_returns is not None else None,
        }

        return result
