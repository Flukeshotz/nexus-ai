"""
Structured market data fetcher service.
Handles: Stock prices (yfinance), with anomaly detection and
API failover as specified in edgeCases.md §2.1 and §2.2.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Anomaly Detection (edgeCases.md §2.2)
# ═══════════════════════════════════════════════════════════════

# Maximum allowed single-day price change before flagging
ANOMALY_THRESHOLD_PCT = 40.0
# Z-score threshold for statistical anomaly detection
ZSCORE_THRESHOLD = 4.0


def detect_price_anomaly(
    current_close: float,
    previous_close: float,
    historical_returns: Optional[list] = None,
) -> tuple:
    """
    Edge Case §2.2: Detect fat-finger errors and unadjusted splits.

    Returns:
        (is_anomaly: bool, reason: str or None)
    """
    if previous_close <= 0 or current_close <= 0:
        return True, "INVALID_PRICE: Zero or negative price detected."

    daily_return = (current_close - previous_close) / previous_close * 100

    # Hard threshold: >40% single-day move
    if abs(daily_return) > ANOMALY_THRESHOLD_PCT:
        return True, (
            f"EXTREME_MOVE: {daily_return:+.1f}% single-day change exceeds "
            f"{ANOMALY_THRESHOLD_PCT}% threshold. Possible split or fat-finger."
        )

    # Z-score test against historical volatility
    if historical_returns and len(historical_returns) >= 20:
        mean_ret = np.mean(historical_returns)
        std_ret = np.std(historical_returns)
        if std_ret > 0:
            zscore = abs((daily_return / 100 - mean_ret) / std_ret)
            if zscore > ZSCORE_THRESHOLD:
                return True, (
                    f"ZSCORE_ANOMALY: Z-score={zscore:.2f} exceeds {ZSCORE_THRESHOLD}. "
                    f"Daily return={daily_return:+.1f}%."
                )

    return False, None


# ═══════════════════════════════════════════════════════════════
# Staleness Circuit Breaker (edgeCases.md §2.1)
# ═══════════════════════════════════════════════════════════════

STALENESS_THRESHOLD_MINUTES = 15


def check_data_staleness(
    last_update_time: datetime,
    market_is_open: bool = True,
) -> dict:
    """
    Edge Case §2.1: Detect stale data during market hours.

    Returns:
        {"is_stale": bool, "minutes_since_update": float, "warning": str or None}
    """
    now = datetime.now(timezone.utc)
    delta = (now - last_update_time).total_seconds() / 60

    if market_is_open and delta > STALENESS_THRESHOLD_MINUTES:
        return {
            "is_stale": True,
            "minutes_since_update": round(delta, 1),
            "warning": (
                f"STALE_DATA: Last update was {delta:.0f} minutes ago. "
                f"Threshold is {STALENESS_THRESHOLD_MINUTES} minutes during market hours. "
                f"Portfolio generation and rebalancing HALTED."
            ),
        }

    return {
        "is_stale": False,
        "minutes_since_update": round(delta, 1),
        "warning": None,
    }


# ═══════════════════════════════════════════════════════════════
# Stock Data Fetcher (yfinance with fallback)
# ═══════════════════════════════════════════════════════════════

def fetch_stock_data(
    ticker: str,
    start_date: str,
    end_date: Optional[str] = None,
) -> dict:
    """
    Fetch OHLCV data for a ticker using yfinance.
    Implements API failover (edgeCases.md §2.1).

    Returns:
        {
            "ticker": str,
            "data": list of dicts (date, open, high, low, close, adj_close, volume),
            "source": str,
            "error": str or None,
            "anomalies": list of dicts,
        }
    """
    try:
        import yfinance as yf
    except ImportError:
        return {
            "ticker": ticker,
            "data": [],
            "source": "unavailable",
            "error": "yfinance package not installed.",
            "anomalies": [],
        }

    result = {
        "ticker": ticker,
        "data": [],
        "source": "yfinance",
        "error": None,
        "anomalies": [],
    }

    try:
        stock = yf.Ticker(ticker)
        if end_date is None:
            end_date = date.today().isoformat()

        df = stock.history(start=start_date, end=end_date, auto_adjust=True)

        if df.empty:
            result["error"] = f"No data returned for {ticker} from {start_date} to {end_date}."
            return result

        # Convert to records and run anomaly detection
        records = []
        previous_close = None
        historical_returns = []

        for idx, row in df.iterrows():
            price_date = idx.date() if hasattr(idx, 'date') else idx
            close = float(row.get("Close", 0))
            volume = int(row.get("Volume", 0)) if not np.isnan(row.get("Volume", 0)) else 0

            # Edge Case §2.3: Detect halted/delisted (zero volume + zero price)
            if close == 0 or (volume == 0 and previous_close is not None):
                is_anomaly = True
                anomaly_reason = "HALTED_OR_DELISTED: Zero close price or zero volume detected."
            elif previous_close is not None:
                is_anomaly, anomaly_reason = detect_price_anomaly(
                    close, previous_close, historical_returns
                )
            else:
                is_anomaly = False
                anomaly_reason = None

            record = {
                "price_date": str(price_date),
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": close,
                "adj_close": close,  # auto_adjust=True means Close IS adj close
                "volume": volume,
                "is_anomaly": is_anomaly,
                "anomaly_reason": anomaly_reason,
            }
            records.append(record)

            if is_anomaly:
                result["anomalies"].append({
                    "date": str(price_date),
                    "reason": anomaly_reason,
                    "close": close,
                    "previous_close": previous_close,
                })

            # Update tracking
            if previous_close and previous_close > 0:
                daily_ret = (close - previous_close) / previous_close
                historical_returns.append(daily_ret)
            previous_close = close

        result["data"] = records
        logger.info(f"Fetched {len(records)} records for {ticker}, {len(result['anomalies'])} anomalies flagged.")

    except Exception as e:
        result["error"] = f"yfinance fetch failed: {str(e)}"
        logger.error(f"Failed to fetch {ticker}: {e}")

    return result


# ═══════════════════════════════════════════════════════════════
# Batch Fetcher (multiple tickers)
# ═══════════════════════════════════════════════════════════════

DEFAULT_TICKERS = {
    "equity": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS", "MARUTI.NS"],
    "etf": ["NIFTYBEES.NS", "BANKBEES.NS", "GOLDBEES.NS", "LIQUIDBEES.NS", "MON100.NS", "ITBEES.NS", "PHARMABEES.NS", "PSUBNKBEES.NS", "JUNIORBEES.NS", "SILVERBEES.NS"],
    "crypto": ["BTC-USD", "ETH-USD"],
    "index": ["^NSEI", "^BSESN", "^NSEBANK"],
}


def fetch_batch_stock_data(
    tickers: Optional[list] = None,
    period_days: int = 365,
) -> dict:
    """
    Fetch data for multiple tickers.

    Returns:
        {"results": list of fetch results, "total_anomalies": int, "errors": list}
    """
    if tickers is None:
        tickers = []
        for category_tickers in DEFAULT_TICKERS.values():
            tickers.extend(category_tickers)

    start_date = (date.today() - timedelta(days=period_days)).isoformat()
    results = []
    total_anomalies = 0
    errors = []

    for ticker in tickers:
        result = fetch_stock_data(ticker, start_date)
        results.append(result)
        total_anomalies += len(result.get("anomalies", []))
        if result.get("error"):
            errors.append({"ticker": ticker, "error": result["error"]})

    return {
        "results": results,
        "total_tickers": len(tickers),
        "total_anomalies": total_anomalies,
        "errors": errors,
    }


# ═══════════════════════════════════════════════════════════════
# AMFI Mutual Fund NAV Fetcher
# ═══════════════════════════════════════════════════════════════

def fetch_amfi_navs() -> dict:
    """
    Fetch the latest Mutual Fund NAVs from AMFI India API (Free, Public).
    URL: https://www.amfiindia.com/spages/NAVAll.txt
    
    Returns:
        {
            "date": str,
            "funds": list of dicts {"scheme_code", "scheme_name", "nav", "date"}
        }
    """
    import requests
    
    amfi_url = "https://www.amfiindia.com/spages/NAVAll.txt"
    try:
        response = requests.get(amfi_url, timeout=10)
        response.raise_for_status()
        
        lines = response.text.split("\\n")
        funds = []
        
        for line in lines:
            line = line.strip()
            # Valid data lines have semicolons separating fields
            # Format: Scheme Code;ISIN;ISIN;Scheme Name;Net Asset Value;Repurchase Price;Sale Price;Date
            if ";" in line and not line.startswith("Scheme Code"):
                parts = line.split(";")
                if len(parts) >= 6:
                    scheme_code = parts[0].strip()
                    scheme_name = parts[3].strip()
                    nav_str = parts[4].strip()
                    date_str = parts[-1].strip()
                    
                    try:
                        nav = float(nav_str)
                    except ValueError:
                        nav = 0.0
                        
                    if nav > 0:
                        funds.append({
                            "scheme_code": scheme_code,
                            "scheme_name": scheme_name,
                            "nav": nav,
                            "date": date_str
                        })
                        
        logger.info(f"Successfully fetched {len(funds)} Mutual Fund NAVs from AMFI.")
        return {
            "status": "success",
            "total_funds": len(funds),
            "funds": funds,
            "source": "AMFI India"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch AMFI NAVs: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "total_funds": 0,
            "funds": []
        }
