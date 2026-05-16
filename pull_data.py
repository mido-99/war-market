"""
Phase 1: Pull historical price data for all tickers and export CSVs.

Run: uv run python pull_data.py
"""

import sys
from pathlib import Path
import pandas as pd
import yfinance as yf

# ── Config ──────────────────────────────────────────────────────────────────

START = "2025-01-02"
END   = "2026-05-01"  # None = today

TICKERS: dict[str, list[str]] = {
    "defense":      ["LMT", "RTX", "NOC"],
    "energy":       ["XOM", "CVX", "USO", "CL=F"],
    "airlines":     ["DAL", "UAL", "AAL"],
    "shipping":     ["ZIM", "MATX"],
    "safe_haven":   ["GLD", "TLT"],
    "broad_market": ["SPY", "QQQ", "^VIX"],
    "big_tech":     ["AAPL", "MSFT", "NVDA", "TSLA", "META"],
    "healthcare":   ["JNJ", "PFE", "UNH", "MRK"],
}

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_ticker(symbol: str, asset_class: str) -> pd.DataFrame:
    """Download one ticker, flatten MultiIndex columns, add metadata cols."""
    raw = yf.download(
        symbol,
        start=START,
        end=END,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        print(f"  [WARN] {symbol}: no data returned", file=sys.stderr)
        return pd.DataFrame()

    # yfinance returns MultiIndex columns when a single ticker is passed via
    # download(); flatten to simple column names.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # Normalise column names
    raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]

    # yfinance with auto_adjust=True folds splits/dividends into prices;
    # the resulting "close" column is already split-adjusted — store it as
    # adj_close so the schema stays consistent.
    if "adj_close" not in raw.columns and "close" in raw.columns:
        raw["adj_close"] = raw["close"]

    # Forward-fill any gaps (market holidays, missing sessions)
    raw = raw.ffill()

    raw.index.name = "date"
    raw = raw.reset_index()

    raw["ticker"]      = symbol
    raw["asset_class"] = asset_class

    # Keep only schema columns (+ whatever extras yfinance returns)
    keep = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "asset_class"]
    available = [c for c in keep if c in raw.columns]
    return raw[available]


