-- 02_create_suppliers_orders_shipments.sql
-- Adds supplier, order, and shipment tables to the schema.
-- These are entirely SYNTHETIC (SPA does not track supply-chain
-- logistics) and support Model 4 (resupply prioritization) and
-- the shipment-risk stretch goal from the project brief.
--
-- Depends on: facilities, commodities (created in 01_create_tables.sql)

-- ============================================================
-- SUPPLIERS
-- Grain: one row = one supplier organization.
-- ============================================================
CREATE TABLE suppliers (
    supplier_id             SERIAL PRIMARY KEY,
    supplier_name             VARCHAR(255) NOT NULL,
    supplier_type              VARCHAR(100),                 -- e.g. 'Government', 'NGO', 'Private Distributor'
    average_lead_time_days      INTEGER,                      -- typical days from order to delivery
    reliability_score            NUMERIC(4,3)                  -- synthetic score 0.000-1.000; historical on-time rate
);

-- ============================================================
-- ORDERS
-- Grain: one row = one commodity resupply order placed by one
-- facility, from one supplier, on one date.
-- ============================================================
CREATE TABLE orders (
    order_id            SERIAL PRIMARY KEY,
    facility_id           INTEGER NOT NULL REFERENCES facilities(facility_id),
    commodity_id           INTEGER NOT NULL REFERENCES commodities(commodity_id),
    supplier_id             INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    order_date               DATE NOT NULL,
    quantity_ordered          INTEGER NOT NULL
);

-- ============================================================
-- SHIPMENTS
-- Grain: one row = the delivery record fulfilling one order.
-- Simplification for MVP: treated as 1:1 with orders (no partial
-- shipment splitting yet).
-- ============================================================
CREATE TABLE shipments (
    shipment_id            SERIAL PRIMARY KEY,
    order_id                 INTEGER NOT NULL REFERENCES orders(order_id),
    dispatch_date              DATE,                          -- NULL until actually dispatched
    expected_arrival_date        DATE,                          -- supplier's promised delivery date
    actual_arrival_date           DATE,                          -- NULL if still in transit/pending
    quantity_shipped               INTEGER,                      -- may differ from quantity_ordered
    shipment_status                 VARCHAR(50)                   -- e.g. 'Pending', 'In Transit', 'Delivered', 'Delayed'
);