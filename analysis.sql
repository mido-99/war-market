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
-- SECTOR AVERAGES  AVG pct_change per asset_class per window
-- (run after TRUNCATE + INSERT above)
-- =============================================================================

SELECT
    window_name,
    asset_class,
    ROUND(AVG(pct_change), 4) AS avg_pct_change,
    COUNT(*)                  AS ticker_count
FROM ticker_windows
GROUP BY window_name, asset_class
ORDER BY window_name, avg_pct_change DESC;


-- =============================================================================
-- VIX DEEP-DIVE  Peak date, spike magnitude, and days to recover
-- Baseline = window_1 average (pre-conflict)
-- =============================================================================

-- Part A: Peak VIX date and spike magnitude per window
WITH vix_baseline AS (
    SELECT ROUND(AVG(adj_close), 2) AS baseline_vix
    FROM prices
    WHERE ticker = '^VIX'
      AND date BETWEEN '2025-01-02' AND '2025-06-12'
),
window_bounds AS (
    SELECT 'window_2'::varchar(20) AS window_name, '2025-06-13'::date AS w_start, '2025-06-24'::date AS w_end
    UNION ALL SELECT 'window_3', '2025-06-25', '2026-02-27'
    UNION ALL SELECT 'window_4', '2026-02-28', '2026-04-07'
    UNION ALL SELECT 'window_5', '2026-04-08', '2026-04-30'
),
vix_per_window AS (
    SELECT
        wb.window_name,
        p.date,
        p.adj_close AS vix_value,
        ROW_NUMBER() OVER (PARTITION BY wb.window_name ORDER BY p.adj_close DESC) AS rn
    FROM prices p
    JOIN window_bounds wb ON p.date BETWEEN wb.w_start AND wb.w_end
    WHERE p.ticker = '^VIX'
)
SELECT
    v.window_name,
    v.date                                    AS peak_date,
    v.vix_value                               AS peak_vix,
    vb.baseline_vix,
    ROUND(v.vix_value - vb.baseline_vix, 2)  AS spike_magnitude
FROM vix_per_window v
CROSS JOIN vix_baseline vb
WHERE v.rn = 1
ORDER BY v.window_name;


-- Part B: Days to recover (calendar days from peak back to baseline)
-- recovery_date is NULL if VIX never returned to baseline within the dataset
WITH vix_baseline AS (
    SELECT ROUND(AVG(adj_close), 2) AS baseline_vix
    FROM prices
    WHERE ticker = '^VIX'
      AND date BETWEEN '2025-01-02' AND '2025-06-12'
),
window_bounds AS (
    SELECT 'window_2'::varchar(20) AS window_name, '2025-06-13'::date AS w_start, '2025-06-24'::date AS w_end
    UNION ALL SELECT 'window_3', '2025-06-25', '2026-02-27'
    UNION ALL SELECT 'window_4', '2026-02-28', '2026-04-07'
    UNION ALL SELECT 'window_5', '2026-04-08', '2026-04-30'
),
vix_peaks AS (
    SELECT DISTINCT ON (wb.window_name)
        wb.window_name,
        p.date        AS peak_date,
        p.adj_close   AS peak_vix
    FROM prices p
    JOIN window_bounds wb ON p.date BETWEEN wb.w_start AND wb.w_end
    WHERE p.ticker = '^VIX'
    ORDER BY wb.window_name, p.adj_close DESC
),
recovery AS (
    SELECT
        vp.window_name,
        vp.peak_date,
        vp.peak_vix,
        MIN(p.date) AS recovery_date
    FROM vix_peaks vp
    CROSS JOIN vix_baseline vb
    JOIN prices p
      ON p.ticker = '^VIX'
     AND p.date > vp.peak_date
     AND p.adj_close <= vb.baseline_vix
    GROUP BY vp.window_name, vp.peak_date, vp.peak_vix
)
SELECT
    r.window_name,
    r.peak_date,
    ROUND(r.peak_vix, 2)                AS peak_vix,
    r.recovery_date,
    (r.recovery_date - r.peak_date)     AS days_to_recover
FROM vix_peaks vp
LEFT JOIN recovery r USING (window_name)
ORDER BY vp.window_name;

---------------------------------------
-- PARTITION Approach
-- Same results with different approach
WITH vix_baseline AS (
    SELECT
        ROUND(AVG(adj_close), 4) AS baseline_vix
    FROM
        prices
    WHERE
        ticker = '^VIX'
        AND date BETWEEN '2025-01-02' AND '2025-06-12'
),
window_bounds AS (
    SELECT 'window_2'::VARCHAR(20) AS window_name, '2025-06-13'::DATE AS w_start, '2025-06-24'::DATE AS w_end
    UNION ALL SELECT 'window_3', '2025-06-25', '2026-02-27'
    UNION ALL SELECT 'window_4', '2026-02-28', '2026-04-07'
    UNION ALL SELECT 'window_5', '2026-04-08', '2026-04-30'
),
vix_per_window AS (
    SELECT
        wb.window_name,
        p.date,
        p.adj_close AS vix_value,
        ROW_NUMBER() OVER(
            PARTITION BY wb.window_name
            ORDER BY p.adj_close DESC
        ) AS peak_rank
    FROM
        prices p
    JOIN
        window_bounds AS wb ON p.date BETWEEN wb.w_start AND wb.w_end
    WHERE
        ticker = '^VIX'
),
vix_peaks AS (
    SELECT
        v.window_name,
        v.date AS peak_date,
        v.vix_value AS peak_vix,
        vb.baseline_vix AS baseline,
        ROUND(v.vix_value - vb.baseline_vix, 4) AS spike_magnitude
    FROM vix_per_window AS v
    CROSS JOIN vix_baseline AS vb
    WHERE
        v.peak_rank = 1
),
vix_recovery_candidates AS (
    SELECT
        vp.window_name,
        vp.peak_date,
        vp.peak_vix,
        vp.spike_magnitude,
        p.date AS recovery_date,
        ROW_NUMBER() OVER(
            PARTITION BY vp.window_name
            ORDER BY p.date ASC
        ) AS recovery_rank
    FROM vix_peaks vp
    INNER JOIN
        prices AS p ON p.ticker = '^VIX'
    WHERE
        p.date > vp.peak_date
        AND p.adj_close <= vp.baseline
)
SELECT
    window_name,
    peak_date,
    peak_vix,
    spike_magnitude,
    recovery_date,
    (recovery_date - peak_date) AS days_to_recover
FROM 
    vix_recovery_candidates
WHERE 
    recovery_rank = 1;