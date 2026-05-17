"""
Phase 2: Create schema, bulk-insert CSVs into prices, seed events table.

Run: uv run python load_db.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# ── Connection ───────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "war_market"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prices (
    ticker      VARCHAR(10)    NOT NULL,
    date        DATE           NOT NULL,
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    adj_close   NUMERIC(12,4),
    volume      BIGINT,
    asset_class VARCHAR(30),
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS events (
    id          SERIAL PRIMARY KEY,
    event_date  DATE         NOT NULL,
    event_name  VARCHAR(200) NOT NULL,
    conflict    VARCHAR(30),
    window_tag  VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS ticker_windows (
    ticker        VARCHAR(10),
    window_name   VARCHAR(20),
    pct_change    NUMERIC(8,4),
    asset_class   VARCHAR(30),
    rank_in_class INTEGER
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices (ticker, date);
CREATE INDEX IF NOT EXISTS idx_prices_date        ON prices (date);
"""

EVENTS = [
    ("2025-06-13", "Israel launches airstrikes on Iran nuclear sites",       "US-Iran-2025", "window_2"),
    ("2025-06-21", "US joins — Operation Midnight Hammer begins",            "US-Iran-2025", "window_2"),
    ("2025-06-24", "Ceasefire announced",                                    "US-Iran-2025", "window_2"),
    ("2026-02-28", "US & Israel launch second major operation against Iran",  "US-Iran-2026", "window_4"),
    ("2026-04-08", "Pakistan-mediated 2-week ceasefire begins; Trump seeks peace deal", "US-Iran-2026", "window_5"),
]


# ── Bulk insert ──────────────────────────────────────────────────────────────

PRICE_COLS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "asset_class"]

def load_csv(conn, csv_path: Path) -> int:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    # Ensure all schema columns exist (volume may be NaN for ^VIX / CL=F)
    for col in PRICE_COLS:
        if col not in df.columns:
            df[col] = None

    df = df[PRICE_COLS].copy()
    # Convert NaN → None so psycopg2 maps to SQL NULL
    records = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO prices (ticker, date, open, high, low, close, adj_close, volume, asset_class)
            VALUES %s
            ON CONFLICT (ticker, date) DO UPDATE SET
                open        = EXCLUDED.open,
                high        = EXCLUDED.high,
                low         = EXCLUDED.low,
                close       = EXCLUDED.close,
                adj_close   = EXCLUDED.adj_close,
                volume      = EXCLUDED.volume,
                asset_class = EXCLUDED.asset_class
            """,
            records,
            page_size=500,
        )
    conn.commit()
    return len(records)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = Path("data")
    csv_files = [f for f in data_dir.glob("*.csv") if f.stem != "all_tickers"]

    if not csv_files:
        print("No per-class CSVs found in data/. Run pull_data.py first.", file=sys.stderr)
        sys.exit(1)

    print("Connecting to PostgreSQL...")
    conn = get_conn()

    # 1. Run schema migrations
    print("Running schema migrations...")
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    print("  Schema ready.")

    # 2. Bulk insert per-class CSVs
    print("\nLoading CSVs into prices table...")
    total_rows = 0
    for csv_path in sorted(csv_files):
        n = load_csv(conn, csv_path)
        print(f"  {csv_path.name:<25} {n:>6,} rows inserted/updated")
        total_rows += n
    print(f"\n  Total: {total_rows:,} rows")

    # 3. Seed events table (idempotent)
    print("\nSeeding events table...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM events")
        cur.executemany(
            "INSERT INTO events (event_date, event_name, conflict, window_tag) VALUES (%s,%s,%s,%s,%s)",
            EVENTS,
        )
    conn.commit()
    print(f"  {len(EVENTS)} events seeded.")

    # 4. Verify
    print("\n-- Row counts per ticker --")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, asset_class, COUNT(*) AS rows
            FROM prices
            GROUP BY ticker, asset_class
            ORDER BY asset_class, ticker
        """)
        rows = cur.fetchall()

    col_w = max(len(r[0]) for r in rows)
    for ticker, asset_class, count in rows:
        flag = " [LOW]" if count < 300 else ""
        print(f"  {ticker:<{col_w}}  {asset_class:<18}  {count:>4}{flag}")

    conn.close()
    print("\nDone. Database is ready for Phase 3 analysis.")


if __name__ == "__main__":
    main()
