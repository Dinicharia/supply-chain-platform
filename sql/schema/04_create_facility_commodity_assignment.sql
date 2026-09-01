-- ~/supply-chain-platform/sql/schema/04_create_facility_commodity_assignment.sql
--
-- Determines WHICH commodities each facility stocks, based on the
-- facility-tier -> service-area eligibility rule designed in Phase 3.
-- This is a structural/business-rule table, separate from the day-to-day
-- inventory_daily simulation that will be built against it.
--
-- Grain: one row = one (facility, commodity) pair that IS eligible to
-- be stocked at that facility. Pairs not eligible simply don't appear
-- here (not represented as a False row) - keeps the table lean and
-- directly usable as "the list of pairs to simulate."

CREATE TABLE facility_commodity_stock_assignment (
    facility_id      INTEGER NOT NULL REFERENCES facilities(facility_id),
    commodity_id       INTEGER NOT NULL REFERENCES commodities(commodity_id),
    PRIMARY KEY (facility_id, commodity_id)
);