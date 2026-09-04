-- ~/supply-chain-platform/sql/analytics/05_risk_score.sql
--
-- Simple rule-based risk/priority score per facility-commodity pair,
-- combining stockout rate with commodity criticality. This is a
-- preview of Phase 9's more sophisticated resupply prioritization
-- model - built here with plain SQL to establish a baseline before
-- any ML or optimization is introduced.
--
-- risk_score = stockout_rate_pct * criticality_weight
-- (Essential commodities weighted 2x Routine, per Finding 4 - since a
-- stockout of an essential medicine has more severe consequences than
-- a routine one, even at the same frequency.)

WITH facility_commodity_stockouts AS (
    SELECT
        i.facility_id,
        i.commodity_id,
        COUNT(*) AS total_days,
        SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_days,
        ROUND(100.0 * SUM(CASE WHEN i.closing_stock = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS stockout_rate_pct
    FROM inventory_daily i
    GROUP BY i.facility_id, i.commodity_id
)
SELECT
    f.facility_name,
    f.facility_tier,
    r.region_name,
    c.commodity_name,
    c.criticality_level,
    fcs.stockout_rate_pct,
    CASE WHEN c.criticality_level = 'Essential' THEN 2.0 ELSE 1.0 END AS criticality_weight,
    ROUND(
        fcs.stockout_rate_pct * (CASE WHEN c.criticality_level = 'Essential' THEN 2.0 ELSE 1.0 END),
        2
    ) AS risk_score
FROM facility_commodity_stockouts fcs
JOIN facilities f ON fcs.facility_id = f.facility_id
JOIN regions r ON f.region_id = r.region_id
JOIN commodities c ON fcs.commodity_id = c.commodity_id
ORDER BY risk_score DESC
LIMIT 20;