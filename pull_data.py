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
    "defense":        ["LMT", "RTX", "NOC", "GD"],
    "drones_autonomy":["AVAV", "KTOS", "PLTR", "LHX"],
    "cybersecurity":  ["CRWD", "PANW", "CIBR"],
    "energy":         ["XOM", "CVX", "USO", "CL=F", "CCJ"],
    "airlines":       ["DAL", "UAL", "AAL"],
    "shipping":       ["HPGLY", "MATX", "FRO"],
    "agri_food":      ["ADM", "BG", "NTR", "CF"],
    "critical_mins":  ["MP"],
    "safe_haven":     ["GLD", "TLT", "BTC-USD"],
    "broad_market":   ["SPY", "QQQ", "^VIX"],
    "big_tech":       ["AAPL", "MSFT", "NVDA", "TSLA", "META"],
    "healthcare":     ["JNJ", "PFE", "UNH", "MRK"],
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    all_frames: list[pd.DataFrame] = []

    for asset_class, symbols in TICKERS.items():
        class_frames: list[pd.DataFrame] = []

        for symbol in symbols:
            print(f"Fetching {symbol} ({asset_class})...")
            df = fetch_ticker(symbol, asset_class)
            if df.empty:
                continue
            class_frames.append(df)
            all_frames.append(df)

        if class_frames:
            class_df = pd.concat(class_frames, ignore_index=True)
            out_path  = DATA_DIR / f"{asset_class}.csv"
            class_df.to_csv(out_path, index=False)
            print(f"  -> saved {out_path}  ({len(class_df):,} rows, {len(class_frames)} tickers)")

    if not all_frames:
        print("No data fetched — check your internet connection.", file=sys.stderr)
        sys.exit(1)

    combined = pd.concat(all_frames, ignore_index=True)
    combined_path = DATA_DIR / "all_tickers.csv"
    combined.to_csv(combined_path, index=False)
    print(f"\nAll tickers combined -> {combined_path}  ({len(combined):,} rows total)")

    # Quick sanity-check summary
    print("\n-- Row counts per ticker --")
    summary = (
        combined.groupby(["asset_class", "ticker"])
        .size()
        .reset_index(name="rows")
        .sort_values(["asset_class", "ticker"])
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
