# US–Iran War Market Impact Analysis — Project Brief

## Goal

Build a data pipeline that pulls historical stock market data, stores it in PostgreSQL,
and analyzes how two major geopolitical events in 2025–2026 affected different market
sectors — identifying winners, losers, and the reasoning behind each movement.
Final output: interactive Plotly charts, SQL-backed analysis, and a published GitHub repo.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| `yfinance` | Pull historical price data |
| `pandas` | Clean and transform data |
| `psycopg2` | Load data into PostgreSQL |
| `PostgreSQL` | Store and query cleaned data |
| `plotly` | Build interactive charts |
| `streamlit` | Dashboard app + free cloud deployment |
| `python-dotenv` | Manage DB credentials via `.env` |

---

## Key Event Dates (tag these in the database)

| Date | Event |
|---|---|
| June 13, 2025 | Israel launches strikes — conflict begins |
| June 21–22, 2025 | US joins with Operation Midnight Hammer |
| June 24, 2025 | Ceasefire announced |
| February 28, 2026 | US & Israel launch second major operation |

---

## Tickers to Track

| Sector | Tickers | yfinance symbols |
|---|---|---|
| Defense | Lockheed Martin, Raytheon, Northrop | `LMT`, `RTX`, `NOC` |
| Energy / Oil | ExxonMobil, Chevron, Oil ETF, WTI Crude | `XOM`, `CVX`, `USO`, `CL=F` |
| Airlines | Delta, United, American | `DAL`, `UAL`, `AAL` |
| Shipping | ZIM, Matson | `ZIM`, `MATX` |
| Safe Havens | Gold ETF, Long-term bonds | `GLD`, `TLT` |
| Broad Market | S&P 500, Nasdaq, Fear Index | `SPY`, `QQQ`, `^VIX` |
| Big Tech | Apple, Microsoft, Nvidia, Tesla, Meta | `AAPL`, `MSFT`, `NVDA`, `TSLA`, `META` |
| Healthcare | Johnson & Johnson, Pfizer, UnitedHealth, Merck | `JNJ`, `PFE`, `UNH`, `MRK` |

---

## Database Schema (use exactly this)

```sql
-- Main price table
CREATE TABLE prices (
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

-- Key event dates reference table
CREATE TABLE events (
    id         SERIAL PRIMARY KEY,
    event_date DATE         NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    conflict   VARCHAR(30),
    window_tag VARCHAR(20)
);

-- Pre-computed % change per ticker per window (populated in Phase 3)
CREATE TABLE ticker_windows (
    ticker        VARCHAR(10),
    window_name   VARCHAR(20),
    pct_change    NUMERIC(8,4),
    asset_class   VARCHAR(30),
    rank_in_class INTEGER
);

-- Indexes
CREATE INDEX idx_prices_ticker_date ON prices (ticker, date);
CREATE INDEX idx_prices_date ON prices (date);
```

---

## Analysis Windows

| Window tag | Name | Date range |
|---|---|---|
| `window_1` | Pre-conflict baseline | Jan 2, 2025 → Jun 12, 2025 |
| `window_2` | 12-Day War | Jun 13, 2025 → Jun 24, 2025 |
| `window_3` | Inter-conflict period | Jun 25, 2025 → Feb 27, 2026 |
| `window_4` | Second operation | Feb 28, 2026 → present |

**% change formula:** `(adj_close[last day of window] - adj_close[first day of window]) / adj_close[first day of window] * 100`

---

## Project Phases

### Phase 1 — Pull & Clean Data
- Use `yfinance.download()` with `auto_adjust=True` for all tickers, date range Jan 2025 → today
- Forward-fill any missing trading days with `.ffill()`
- Add `ticker` and `asset_class` columns to each DataFrame
- Export one CSV per asset class as a backup

**Output:** Clean CSV files for all 20 tickers

---

### Phase 2 — Load into PostgreSQL
- Create the database and run the schema migrations above
- Bulk-insert all CSVs into the `prices` table
- Seed the `events` table with the 4 key dates above
- Verify with: `SELECT ticker, COUNT(*) FROM prices GROUP BY ticker ORDER BY 1`

**Output:** Fully populated database ready for queries

---

### Phase 3 — Analysis Queries
- Write a CTE that tags every row in `prices` with its window (`window_1` through `window_4`)
- Calculate % change per ticker per window using the formula above
- Use `RANK() OVER (PARTITION BY window_name ORDER BY pct_change DESC)` to rank winners and losers
- Insert results into the `ticker_windows` table

**Output:** `ticker_windows` table populated + save the SQL as `analysis.sql`

---

### Phase 4 — Streamlit Dashboard
Build a Streamlit web app (`app.py`) that queries PostgreSQL directly and renders all 4
charts using Plotly. The app should feel like a real product — not a static page.

**Sidebar filters (update all charts live when changed):**
- Conflict window selector — `window_1` through `window_4`
- Sector multiselect — filter charts to one or more asset classes

**Charts to include (use `st.plotly_chart(fig, use_container_width=True)`):**
1. **Sector comparison bar chart** — % change per asset class per window, grouped bars
2. **Normalized price overlay** — all tickers rebased to 100 at conflict start, showing divergence
3. **VIX spike chart** — VIX over time with vertical dashed lines at each event date
4. **Winners vs losers** — top 5 and bottom 5 tickers for the selected window, horizontal bar chart

Add event date annotations (`fig.add_vline()`) to all time-series charts.

**Deployment (free, public URL):**
- Push `app.py` to the GitHub repo
- Go to [streamlit.io/cloud](https://streamlit.io/cloud), connect the repo, set the entry point to `app.py`
- Add PostgreSQL credentials as Streamlit secrets (replaces `.env` in production)
- Live URL will be `your-name-war-analysis.streamlit.app` — put this on your resume and LinkedIn

**Output:** Live public Streamlit dashboard at a shareable URL

---

### Phase 5 — Write-up & Publish
Write a short narrative conclusion covering:
- Why defense stocks moved (contract expectations, threat posture)
- Why energy reacted (Strait of Hormuz closure risk)
- Why airlines dropped (fuel cost + demand shock)
- Why gold and bonds spiked (flight to safety)
- What the VIX spike shape tells us about how fast the market processed the news

Then:
- Push everything to GitHub with a clean `README.md`
- Publish 3 LinkedIn posts (see milestones below)

**Output:** Public GitHub repo + 3 LinkedIn posts

---

## LinkedIn Post Milestones

| Post | When to publish | Hook |
|---|---|---|
| Post 1 | After Phase 2 | "Built a data pipeline that pulls 20 market tickers and stores them in PostgreSQL — here's what the raw data looks like before analysis." |
| Post 2 | After Phase 4 | "Built a live interactive dashboard — filter by sector and conflict window to explore which stocks won and lost. Link in comments." + dashboard URL |
| Post 3 | After Phase 5 | "Full analysis complete — how geopolitics moved the market and why each sector reacted the way it did." |

---

## Project Structure

```
war-market-analysis/
├── .env                  # DB credentials (gitignored)
├── pull_data.py          # Phase 1: yfinance pull + clean + export CSVs
├── load_db.py            # Phase 2: create tables + bulk insert
├── analysis.sql          # Phase 3: window CTEs + ranking queries
├── app.py                # Phase 4: Streamlit dashboard (entry point)
├── data/                 # CSV backups (gitignored)
└── README.md
```

---

## Notes for Implementation

- Use `python-dotenv` and a `.env` file for all PostgreSQL credentials — never hardcode them
- Use `adj_close` for all % change calculations; use `close` only for raw price charts
- `CL=F` (WTI crude) and `^VIX` behave differently from equity tickers in yfinance — test these first
- PostgreSQL running locally is fine (no cloud setup needed for a portfolio project)
