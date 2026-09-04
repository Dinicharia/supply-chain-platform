-- ~/supply-chain-platform/sql/analytics/02_stockout_by_dimension.sql
--
-- Breaks down the overall 10.68% stockout rate by region, facility
-- tier, and commodity - answers "where is risk concentrated?" (core
-- business question from Section 6 of the project brief).

-- Q1: Stockout rate by facility tier. Hypothesis to check: do larger
-- facilities (more consumption, but also bigger order-up-to buffers)
-- have better or worse stockout rates than small ones?
SELECT
    f.facility_tier,
    COUNT(*) AS total_days,
    SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
FROM inventory_daily i
JOIN facilities f ON i.facility_id = f.facility_id
GROUP BY f.facility_tier
ORDER BY stockout_rate_pct DESC;

-- Q2: Stockout rate by region. Which regions are highest-risk?
SELECT
    r.region_name,
    COUNT(*) AS total_days,
    SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
FROM inventory_daily i
JOIN facilities f ON i.facility_id = f.facility_id
JOIN regions r ON f.region_id = r.region_id
GROUP BY r.region_name
ORDER BY stockout_rate_pct DESC;

-- Q3: Stockout rate by commodity, including criticality - this is the
-- most operationally important breakdown, since an "Essential" drug
-- stocking out matters far more than a "Routine" one.
SELECT
    c.commodity_name,
    c.criticality_level,
    COUNT(*) AS total_days,
    SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
FROM inventory_daily i
JOIN commodities c ON i.commodity_id = c.commodity_id
GROUP BY c.commodity_name, c.criticality_level
ORDER BY stockout_rate_pct DESC;