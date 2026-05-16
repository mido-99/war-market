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
