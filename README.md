# 🪖 War Market Analysis

> How do financial markets respond to armed conflict?

This project tracks the price behavior of 80+ US-listed tickers across 12 asset classes during the US–Iran conflict events of 2025–2026. Data is sliced into 5 conflict windows and analyzed for % change, sector rankings, normalized price trends, and VIX behavior.

Status: Phases 1–5 complete ✅

---

## ⏱️ Conflict Windows

| Window | Label | Period |
|--------|-------|--------|
| window_1 | Pre-conflict baseline | 2025-01-02 → 2025-06-12 |
| window_2 | 12-Day War | 2025-06-13 → 2025-06-24 |
| window_3 | Inter-conflict period | 2025-06-25 → 2026-02-27 |
| window_4 | Second operation | 2026-02-28 → 2026-04-07 |
| window_5 | Ceasefire / peace deal | 2026-04-08 → 2026-04-30 |

---

## 🏭 Asset Classes

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

## 🛠️ Stack

- **Python** — pandas, yfinance
- **PostgreSQL** — psycopg2
- **Dashboard** — Streamlit + Plotly

---

## 📁 Project Structure

```
war_market/
├── pull_data.py      # Phase 1 — fetch & clean data via yfinance
├── analysis.sql      # Phase 3 — window tagging, % change, VIX deep-dive
├── app.py            # Phase 4 — Streamlit dashboard
├── data/
│   ├── defense.csv
│   ├── energy.csv
│   ├── ...           # one CSV per asset class
│   └── all_tickers.csv
└── .env              # DB credentials (not committed)
```

---

## ⚙️ Setup

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

## 🗄️ Database Schema (simplified)

```sql
prices         (ticker, date, adj_close, asset_class, ...)
events         (event_name, start_date, end_date)
ticker_windows (ticker, window_name, pct_change, asset_class, rank_in_class)
```

---

## 📊 Dashboard

The Streamlit dashboard (`app.py`) has four interactive charts, all filterable by conflict window and sector via the sidebar:

| # | Chart | What it shows |
|---|-------|---------------|
| 1 | **Sector Performance by Window** | Average % price change per sector per conflict phase (bar chart) |
| 2 | **Normalized Price Overlay** | Daily price series rebased to 100 at conflict start — sector averages with event markers |
| 3 | **VIX Spike** | VIX daily close across the full timeline with conflict phase markers |
| 4 | **Winners vs Losers** | Top and bottom individual tickers ranked by % change within the selected window |

---

## 📝 Analysis & Findings

> All numbers from the `ticker_windows` table. Sector avg = mean % change across all tickers in that class for that window.

### Defense — "Buy the Rumor, Sell the War"

| Window | Sector avg | Standouts |
|--------|-----------|-----------|
| Pre-conflict (W1) | **+13.53%** | BWXT +24.2%, HII +23.8%, RTX +22.8% |
| 12-Day War (W2) | **−0.83%** | LMT −5.4%, NOC −6.3% |
| Inter-conflict (W3) | **+36.67%** | HII +91.4%, NOC +50.4%, BWXT +46.7% |
| Second operation (W4) | **−7.96%** | HII −11.3%, LDOS −11.2% |
| Ceasefire (W5) | **−8.10%** | LMT −17.6%, NOC −15.7% |

- Defense was priced for war *before* it started (+13.5% pre-conflict) — when strikes began, the sector went *down* −0.83%.
- The real gains came during the inter-conflict calm, when procurement replenishment orders became concrete (HII +91%, NOC +50%).
- Both the second operation and ceasefire triggered further sell-offs — the war thesis had fully unwound.

---

### Energy — Oil Went the *Wrong* Way in the 12-Day War

| Window | Sector avg | Standouts |
|--------|-----------|-----------|
| Pre-conflict (W1) | **+2.16%** | CCJ +26.8%, SHEL +15.7% |
| 12-Day War (W2) | **−4.96%** | CL=F −11.8%, USO −9.0%, XOM −3.4% |
| Inter-conflict (W3) | **+39.51%** | HAL +80.2%, CCJ +66.1%, SLB +58.1% |
| Second operation (W4) | **+17.23%** | CL=F +58.6%, USO +58.4% |
| Ceasefire (W5) | **+6.43%** | USO +18.1%, HAL +11.9% |

- WTI crude fell −11.8% during the actual war — the Hormuz closure risk premium evaporated as soon as a ceasefire looked likely.
- The real oil spike came in the second operation: CL=F +58.6%, USO +58.4% — the largest single-window move of any asset in the dataset.
- Oilfield services (HAL +80%, SLB +58%) outpaced integrated majors (XOM +44%) in the recovery, reflecting higher operational leverage.

---

### Airlines — They *Gained* During the 12-Day War

| Window | Sector avg | Standouts |
|--------|-----------|-----------|
| Pre-conflict (W1) | **−10.56%** | AAL −35.9%, ALK −22.8%, DAL −16.8% |
| 12-Day War (W2) | **+5.11%** | AAL +9.6%, UAL +6.8%, DAL +5.4% |
| Inter-conflict (W3) | **+30.12%** | LUV +58.8%, UAL +38.5%, DAL +37.3% |
| Second operation (W4) | **−14.04%** | ALK −27.3%, LUV −21.2% |
| Ceasefire (W5) | **−4.51%** | RYAAY −14.9%, UAL −6.5% |

- All six airline tickers gained during the 12-Day War — the opposite of what theory predicts.
- Why: oil fell (improving margins) and airlines were already heavily discounted pre-conflict (AAL −35.9%), so a bounded war was actually a relief.
- The double-compression (oil spike + demand shock) only materialized in the second operation (W4), where airlines fell −14%.

---

### Safe Havens — Gold Fell During the War; Bitcoin Moved in Reverse

| Window | Sector avg | Standouts |
|--------|-----------|-----------|
| Pre-conflict (W1) | **+4.27%** | GLD +27.2%, SLV +22.8% |
| 12-Day War (W2) | **−0.88%** | TLT +1.2%, GLD −3.2% |
| Inter-conflict (W3) | **+21.86%** | SLV +157.5%, GLD +57.5%; BTC-USD −38.6% |
| Second operation (W4) | **−1.55%** | GLD −11.9%, SLV −19.2%; BTC-USD +7.4% |
| Ceasefire (W5) | **+0.53%** | BTC-USD +7.3%; GLD −2.5% |

- GLD fell −3.2% during the war — too short for the flight-to-safety mechanism to engage.
- The real precious metals move came later: Silver +157.5% and Gold +57.5% in the inter-conflict period.
- Bitcoin consistently moved *opposite* to gold/silver: down when metals surged, up when metals fell. No "digital gold" behavior observed.

---

### VIX — The Market Barely Flinched at the 12-Day War

| Window | Peak VIX | Spike above baseline | Recovered in |
|--------|---------|---------------------|-------------|
| Baseline | 21.41 | — | — |
| 12-Day War (W2) | **21.60** | **+0.19** | **1 day** |
| Inter-conflict (W3) | **26.42** | +5.01 | 4 days |
| Second operation (W4) | **31.05** | **+9.64** | **Never** |
| Ceasefire (W5) | **21.04** | −0.37 | 1 day |

- The 12-Day War generated a VIX spike of just +0.19 — statistically negligible, gone in one trading day.
- Each escalation produced a larger and longer spike: +0.19 → +5.01 → +9.64.
- The second operation's VIX never recovered within the window — the only phase the market couldn't price to resolution.
- Post-ceasefire VIX (21.04) closed *below* the pre-conflict baseline, suggesting the peace deal removed a persistent tail risk.

---

## 🗺️ Roadmap

- [x] Phase 1 — Pull & clean data (yfinance → CSVs)
- [x] Phase 2 — Load into PostgreSQL
- [x] Phase 3 — Window analysis, sector averages, VIX deep-dive
- [x] Phase 4 — Streamlit dashboard
  - [x] Sector performance bar chart
  - [x] Normalized price overlay (rebased to conflict start)
  - [x] VIX timeline chart
  - [x] Winners vs losers per window
- [x] Phase 5 — Write-up & publish
  - [x] Defense narrative
  - [x] Energy narrative
  - [x] Airlines narrative
  - [x] Safe havens narrative
  - [x] VIX narrative
  - [x] README finalized
