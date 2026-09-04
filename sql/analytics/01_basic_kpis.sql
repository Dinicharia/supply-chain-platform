-- ~/supply-chain-platform/sql/analytics/01_basic_kpis.sql
--
-- Basic aggregate KPIs: facility counts, overall stockout rate, and
-- commodity coverage. These are the simplest possible "Executive
-- Overview" numbers - a sanity check on the whole platform before
-- we dig into more detailed breakdowns.

-- Q1: How many facilities do we have, by tier?
SELECT facility_tier, COUNT(*) AS facility_count
FROM facilities
GROUP BY facility_tier
ORDER BY facility_count DESC;

-- Q2: How many facilities per region?
SELECT r.region_name, COUNT(f.facility_id) AS facility_count
FROM regions r
JOIN facilities f ON r.region_id = f.region_id
GROUP BY r.region_name
ORDER BY facility_count DESC;

-- Q3: Overall stockout rate across ALL simulated inventory_daily rows.
-- This is our single most important "Executive Overview" number -
-- what fraction of all facility-commodity-days had zero stock?
SELECT
    COUNT(*) AS total_days,
    SUM(CASE WHEN closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
    ROUND(
        100.0 * SUM(CASE WHEN closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS stockout_rate_pct
FROM inventory_daily;

-- Q4: How many distinct facility-commodity pairs are we tracking, and
-- how many commodities does the average facility carry?
SELECT
    COUNT(DISTINCT facility_id) AS distinct_facilities,
    COUNT(DISTINCT commodity_id) AS distinct_commodities,
    COUNT(*) AS total_assigned_pairs,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT facility_id), 2) AS avg_commodities_per_facility
FROM facility_commodity_stock_assignment;