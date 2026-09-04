-- ~/supply-chain-platform/sql/analytics/04_supplier_performance.sql
--
-- Supplier delivery performance: average delay, on-time rate, and
-- partial-fulfillment rate per supplier. Validates whether the
-- reliability_score we assigned each supplier back in Phase 4
-- actually produces a detectable difference in real delivery outcomes.

SELECT
    s.supplier_name,
    s.supplier_type,
    s.reliability_score,
    COUNT(sh.shipment_id) AS total_shipments,
    -- Only DELIVERED shipments have a real actual_arrival_date to compare.
    ROUND(AVG(sh.actual_arrival_date - sh.expected_arrival_date) FILTER (WHERE sh.shipment_status = 'Delivered'), 2) AS avg_delay_days,
    ROUND(
        100.0 * SUM(CASE WHEN sh.shipment_status = 'Delivered' AND sh.actual_arrival_date <= sh.expected_arrival_date THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN sh.shipment_status = 'Delivered' THEN 1 ELSE 0 END), 0),
        2
    ) AS on_time_rate_pct,
    ROUND(
        100.0 * SUM(CASE WHEN sh.quantity_shipped < o.quantity_ordered THEN 1 ELSE 0 END) / COUNT(sh.shipment_id),
        2
    ) AS partial_fulfillment_rate_pct
FROM shipments sh
JOIN orders o ON sh.order_id = o.order_id
JOIN suppliers s ON o.supplier_id = s.supplier_id
GROUP BY s.supplier_name, s.supplier_type, s.reliability_score
ORDER BY s.reliability_score DESC;