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
    # Prime contractors + shipbuilding (HII) + components (TDG) + defense IT (LDOS) + nuclear (BWXT) + Boeing
    "defense":        ["LMT", "RTX", "NOC", "GD", "HII", "TDG", "LDOS", "BWXT", "BA"],

    # UAS/drones (AVAV, KTOS, RCAT), defense AI (PLTR, AI=C3.ai), electronics (LHX), satellite comms (IRDM)
    "drones_autonomy":["AVAV", "KTOS", "PLTR", "LHX", "RCAT", "AI", "IRDM"],

    # US leaders (CRWD, PANW), sector ETF (CIBR), Fortinet, Zscaler, SentinelOne, CyberArk (Israeli)
    "cybersecurity":  ["CRWD", "PANW", "CIBR", "FTNT", "ZS", "S", "CYBR"],

    # Integrated majors (XOM, CVX), crude ETF/futures (USO, CL=F), uranium (CCJ),
    # oilfield services (SLB, HAL), European majors (BP, SHEL)
    "energy":         ["XOM", "CVX", "USO", "CL=F", "CCJ", "SLB", "HAL", "BP", "SHEL"],

    # US big-3 + Southwest, Alaska, Ryanair ADR (European exposure)
    "airlines":       ["DAL", "UAL", "AAL", "LUV", "ALK", "RYAAY"],

    # Hapag-Lloyd ADR, Matson, Frontline + ZIM (Israeli!), Star Bulk, Golden Ocean, Danaos
    "shipping":       ["HPGLY", "MATX", "FRO", "ZIM", "SBLK", "GOGL", "DAC"],

    # Grain traders (ADM, BG), fertilizers (NTR, CF, MOS), ICL (Israeli miner/fertilizer),
    # crop protection (CTVA), equipment (DE)
    "agri_food":      ["ADM", "BG", "NTR", "CF", "MOS", "ICL", "CTVA", "DE"],

    # Rare earths (MP), lithium (ALB, SQM, LAC), copper (FCX), diversified miner (RIO),
    # uranium (UUUU, DNN, LEU)
    "critical_mins":  ["MP", "ALB", "SQM", "FCX", "RIO", "UUUU", "DNN", "LEU", "LAC"],

    # Gold (GLD), bonds long/short (TLT, SHY), broad bonds (AGG), silver (SLV),
    # USD index (UUP), crypto (BTC-USD, ETH-USD)
    "safe_haven":     ["GLD", "TLT", "BTC-USD", "SLV", "AGG", "SHY", "UUP", "ETH-USD"],

    # US broad market (SPY, QQQ, DIA, IWM), volatility (^VIX), emerging markets (EEM)
    "broad_market":   ["SPY", "QQQ", "^VIX", "DIA", "IWM", "EEM"],

    # Original 5 + Alphabet, Amazon (defense cloud contracts), AMD (AI chips)
    "big_tech":       ["AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN", "AMD"],

    # Original 4 + Abbott, AbbVie, Amgen, Medtronic (devices relevant for wartime medical demand)
    "healthcare":     ["JNJ", "PFE", "UNH", "MRK", "ABT", "ABBV", "AMGN", "MDT"],
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
