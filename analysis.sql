-- =============================================================================
-- Phase 3: Window analysis — % change per ticker per conflict window
-- =============================================================================

-- Window definitions (hardcoded; mirrors events table boundaries)
--   window_1  Pre-conflict baseline    2025-01-02 → 2025-06-12
--   window_2  12-Day War               2025-06-13 → 2025-06-24
--   window_3  Inter-conflict period    2025-06-25 → 2026-02-27
--   window_4  Second operation         2026-02-28 → 2026-04-07
--   window_5  Ceasefire / peace deal   2026-04-08 → 2026-04-30

-- =============================================================================
-- STEP 1  Tag every prices row with its window
-- =============================================================================

WITH window_bounds AS (
    SELECT 'window_1'::varchar(20) AS window_name,
           '2025-01-02'::date      AS w_start,
           '2025-06-12'::date      AS w_end
    UNION ALL SELECT 'window_2', '2025-06-13', '2025-06-24'
    UNION ALL SELECT 'window_3', '2025-06-25', '2026-02-27'
    UNION ALL SELECT 'window_4', '2026-02-28', '2026-04-07'
    UNION ALL SELECT 'window_5', '2026-04-08', '2026-04-30'
),

-- STEP 2  For each (ticker, window) find the first and last actual trading day
--         Using real trading days avoids issues when a window boundary falls on
--         a weekend or holiday and no row exists for that exact date.
first_last AS (
    SELECT
        p.ticker,
        p.asset_class,
        wb.window_name,
        MIN(p.date) AS first_date,
        MAX(p.date) AS last_date
    FROM prices p
    JOIN window_bounds wb
      ON p.date BETWEEN wb.w_start AND wb.w_end
    GROUP BY p.ticker, p.asset_class, wb.window_name
),

-- STEP 3  Pull adj_close for the first and last trading day of each window
prices_at_ends AS (
    SELECT
        fl.ticker,
        fl.asset_class,
        fl.window_name,
        p_start.adj_close AS start_price,
        p_end.adj_close   AS end_price
    FROM first_last fl
    JOIN prices p_start
      ON p_start.ticker = fl.ticker AND p_start.date = fl.first_date
    JOIN prices p_end
      ON p_end.ticker   = fl.ticker AND p_end.date   = fl.last_date
),

-- STEP 4  Compute % change and rank within each (window, asset_class)
ranked AS (
    SELECT
        ticker,
        window_name,
        ROUND(
            (end_price - start_price) / NULLIF(start_price, 0) * 100,
            4
        ) AS pct_change,
        asset_class,
        RANK() OVER (
            PARTITION BY window_name, asset_class
            ORDER BY
                ROUND((end_price - start_price) / NULLIF(start_price, 0) * 100, 4) DESC
        ) AS rank_in_class
    FROM prices_at_ends
)

-- =============================================================================
-- FINAL SELECT  (swap this out for INSERT below when ready to persist)
-- =============================================================================
SELECT
    window_name,
    asset_class,
    ticker,
    pct_change,
    rank_in_class
FROM ranked
ORDER BY window_name, asset_class, rank_in_class;


-- =============================================================================
-- SAMPLE TEST — run these individually to eyeball a handful of tickers
-- =============================================================================

-- Defense stocks across all windows
-- SELECT window_name, ticker, pct_change, rank_in_class
-- FROM ranked
-- WHERE asset_class = 'defense'
-- ORDER BY window_name, rank_in_class;

-- SPY + VIX during the 12-Day War
-- SELECT window_name, ticker, pct_change
-- FROM ranked
-- WHERE ticker IN ('SPY', '^VIX', 'GLD', 'TLT') AND window_name = 'window_2'
-- ORDER BY pct_change DESC;


-- =============================================================================
-- PERSIST  Populate ticker_windows (run after verifying the SELECT above)
-- =============================================================================

TRUNCATE ticker_windows;

INSERT INTO ticker_windows (ticker, window_name, pct_change, asset_class, rank_in_class)
WITH window_bounds AS (
    SELECT 'window_1'::varchar(20) AS window_name,
           '2025-01-02'::date      AS w_start,
           '2025-06-12'::date      AS w_end
    UNION ALL SELECT 'window_2', '2025-06-13', '2025-06-24'
    UNION ALL SELECT 'window_3', '2025-06-25', '2026-02-27'
    UNION ALL SELECT 'window_4', '2026-02-28', '2026-04-07'
    UNION ALL SELECT 'window_5', '2026-04-08', '2026-04-30'
),
first_last AS (
    SELECT
        p.ticker, p.asset_class, wb.window_name,
        MIN(p.date) AS first_date,
        MAX(p.date) AS last_date
    FROM prices p
    JOIN window_bounds wb ON p.date BETWEEN wb.w_start AND wb.w_end
    GROUP BY p.ticker, p.asset_class, wb.window_name
),
prices_at_ends AS (
    SELECT
        fl.ticker, fl.asset_class, fl.window_name,
        p_start.adj_close AS start_price,
        p_end.adj_close   AS end_price
    FROM first_last fl
    JOIN prices p_start ON p_start.ticker = fl.ticker AND p_start.date = fl.first_date
    JOIN prices p_end   ON p_end.ticker   = fl.ticker AND p_end.date   = fl.last_date
),
ranked AS (
    SELECT
        ticker, window_name,
        ROUND((end_price - start_price) / NULLIF(start_price, 0) * 100, 4) AS pct_change,
        asset_class,
        RANK() OVER (
            PARTITION BY window_name, asset_class
            ORDER BY ROUND((end_price - start_price) / NULLIF(start_price, 0) * 100, 4) DESC
        ) AS rank_in_class
    FROM prices_at_ends
)
SELECT ticker, window_name, pct_change, asset_class, rank_in_class FROM ranked;

-- =============================================================================

-- Part A: Peak VIX date and spike magnitude per window
