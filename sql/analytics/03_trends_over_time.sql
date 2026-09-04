-- ~/supply-chain-platform/sql/analytics/03_trends_over_time.sql
--
-- Time-based analysis: monthly stockout rate trend, and a rolling
-- 3-month average using a window function. Also isolates malaria
-- commodities specifically to visually confirm the seasonality
-- pattern discussed in Finding 4 of docs/analytics_findings.md.

-- Q1: Monthly stockout rate across the full 5-year simulation.
-- DATE_TRUNC('month', ...) collapses each date down to the first of
-- its month, letting us GROUP BY month regardless of day.
SELECT
    DATE_TRUNC('month', inventory_date)::date AS month,
    COUNT(*) AS total_days,
    SUM(CASE WHEN closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
    ROUND(100.0 * SUM(CASE WHEN closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
FROM inventory_daily
GROUP BY DATE_TRUNC('month', inventory_date)
ORDER BY month;

-- Q2: Same monthly breakdown, but ONLY for Malaria commodities - this
-- should visibly show higher stockout rates in Mar-May and Oct-Dec
-- (Kenya's rainy seasons), confirming the seasonal_multiplier() logic
-- from the simulation is actually producing a detectable real effect.
SELECT
    DATE_TRUNC('month', i.inventory_date)::date AS month,
    ROUND(100.0 * SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
FROM inventory_daily i
JOIN commodities c ON i.commodity_id = c.commodity_id
WHERE c.service_area = 'Malaria'
GROUP BY DATE_TRUNC('month', i.inventory_date)
ORDER BY month;

-- Q3: Rolling 3-month average stockout rate, using a WINDOW FUNCTION.
-- Unlike GROUP BY (which collapses rows), a window function computes
-- an aggregate "over a window" of nearby rows while keeping every row
-- in the output - here, the average of the current month plus the
-- 2 preceding months, smoothing out month-to-month noise.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', inventory_date)::date AS month,
        ROUND(100.0 * SUM(CASE WHEN closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
    FROM inventory_daily
    GROUP BY DATE_TRUNC('month', inventory_date)
)
SELECT
    month,
    stockout_rate_pct,
    ROUND(
        AVG(stockout_rate_pct) OVER (
            ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_3mo_avg_pct
FROM monthly
ORDER BY month;