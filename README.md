# War Market Analysis

> How do financial markets respond to armed conflict?

This project tracks the price behavior of 80+ US-listed tickers across 12 asset classes during the US-Iran conflict events of 2025–2026. Data is sliced into 5 conflict windows and analyzed for % change, sector rankings, and VIX behavior.

**Status: Phases 1–3 complete. Dashboard (Phase 4) in progress.**

---

## Conflict Windows

| Window | Label | Period |
|--------|-------|--------|
| window_1 | Pre-conflict baseline | 2025-01-02 → 2025-06-12 |
| window_2 | 12-Day War | 2025-06-13 → 2025-06-24 |
| window_3 | Inter-conflict period | 2025-06-25 → 2026-02-27 |
| window_4 | Second operation | 2026-02-28 → 2026-04-07 |
| window_5 | Ceasefire / peace deal | 2026-04-08 → 2026-04-30 |

---

## Asset Classes

| Class | Example Tickers |
|-------|----------------|
| defense | LMT, RTX, NOC, GD, BA |
| drones_autonomy | AVAV, KTOS, PLTR, LHX |
| cybersecurity | CRWD, PANW, FTNT, ZS |
| energy | XOM, CVX, USO, SLB |
| airlines | DAL, UAL, AAL, LUV |
| shipping | FRO, ZIM, MATX, SBLK |
| agri_food | ADM, BG, NTR, MOS |
| critical_mins | MP, ALB, FCX, RIO |
| safe_haven | GLD, TLT, BTC-USD, SLV |
| broad_market | SPY, QQQ, ^VIX, IWM |
| big_tech | AAPL, MSFT, NVDA, AMZN |
| healthcare | JNJ, PFE, UNH, MRK |

---

## Stack

- **Python** — pandas, yfinance
- **PostgreSQL** — psycopg2
- **Dashboard** — Streamlit + Plotly

---

## Project Structure

```
war_market/
├── pull_data.py      # Phase 1 — fetch & clean data via yfinance
├── analysis.sql      # Phase 3 — window tagging, % change, VIX deep-dive
├── app.py            # Phase 4 — Streamlit dashboard (in progress)
├── data/
│   ├── defense.csv
│   ├── energy.csv
│   ├── ...           # one CSV per asset class
│   └── all_tickers.csv
└── .env              # DB credentials (not committed)
```

---

## Setup

**1. Install dependencies**

```bash
uv sync
```

**2. Configure environment**

Create a `.env` file:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=war_market
DB_USER=postgres
DB_PASSWORD=your_password
```

**3. Pull data**

```bash
uv run python pull_data.py
```

Fetches ~330 trading days per ticker and writes CSVs to `data/`.

**4. Load into PostgreSQL**

Create the database and run schema migrations, then bulk-insert the CSVs into the `prices` table via psycopg2. Seed the `events` table with the 4 conflict dates.

**5. Run analysis**

Execute `analysis.sql` in order:
1. The main CTE computes `% change` per ticker per window and inserts into `ticker_windows`.
2. Sector averages query aggregates by `asset_class`.
3. VIX deep-dive queries surface peak date, spike magnitude, and recovery time per window.

**6. Launch dashboard**

```bash
uv run streamlit run app.py
```

---

## Database Schema (simplified)

```sql
prices        (ticker, date, adj_close, asset_class, ...)
events        (event_name, start_date, end_date)
ticker_windows (ticker, window_name, pct_change, asset_class, rank_in_class)
```

---

## Roadmap

- [x] Phase 1 — Pull & clean data (yfinance → CSVs)
- [x] Phase 2 — Load into PostgreSQL
- [x] Phase 3 — Window analysis, sector averages, VIX deep-dive
- [ ] Phase 4 — Streamlit dashboard
  - [x] Sector performance bar chart
  - [ ] Winners / losers table per window
  - [ ] VIX timeline chart
  - [ ] Ticker drill-down
