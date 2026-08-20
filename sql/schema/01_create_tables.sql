-- 01_create_tables.sql
-- Creates the core schema for the Global Health Supply Chain
-- Risk & Stockout Prediction Platform (MVP scope: Kenya).
--
-- Table creation order matters: a table with a FOREIGN KEY must be
-- created AFTER the table it references. Order here follows the
-- dependency chain: countries -> regions -> facilities ->
-- commodities -> (facility_commodity_readiness, inventory_daily).

-- ============================================================
-- COUNTRIES
-- Grain: one row = one country. Tiny reference table.
-- ============================================================
CREATE TABLE countries (
    country_id      SERIAL PRIMARY KEY,        -- auto-incrementing surrogate key
    country_name    VARCHAR(100) NOT NULL,     -- e.g. 'Kenya'
    iso_code        CHAR(3) NOT NULL UNIQUE     -- e.g. 'KEN' (ISO 3166-1 alpha-3)
);

-- ============================================================
-- REGIONS
-- Grain: one row = one region/county within a country.
-- ============================================================
CREATE TABLE regions (
    region_id       SERIAL PRIMARY KEY,
    country_id      INTEGER NOT NULL REFERENCES countries(country_id),
    region_name     VARCHAR(100) NOT NULL      -- e.g. 'Nairobi', 'Kisumu'
);

-- ============================================================
-- FACILITIES
-- Grain: one row = one health facility, with static descriptive
-- attributes as observed in the Kenya 2010 SPA survey.
-- ============================================================
CREATE TABLE facilities (
    facility_id         SERIAL PRIMARY KEY,
    region_id           INTEGER NOT NULL REFERENCES regions(region_id),
    facility_name        VARCHAR(255),                  -- may be anonymized/generic per DHS terms
    facility_type         VARCHAR(100),                  -- e.g. 'Hospital', 'Health Center', 'Dispensary'
    managing_authority     VARCHAR(100),                  -- e.g. 'Public', 'Private', 'NGO'
    latitude              NUMERIC(9,6),                  -- GPS coordinate (from SPA GPS dataset)
    longitude             NUMERIC(9,6),
    survey_year            INTEGER NOT NULL DEFAULT 2010   -- anchors this as the SPA 2010 snapshot
);

-- ============================================================
-- COMMODITIES
-- Grain: one row = one distinct commodity tracked by the platform.
-- ============================================================
CREATE TABLE commodities (
    commodity_id        SERIAL PRIMARY KEY,
    commodity_name        VARCHAR(255) NOT NULL,         -- e.g. 'Amoxicillin 500mg'
    category               VARCHAR(100),                  -- e.g. 'Antibiotic', 'Diagnostic'
    service_area            VARCHAR(100),                  -- e.g. 'TB', 'HIV/ART', 'Malaria', 'Family Planning'
    criticality_level        VARCHAR(50),                   -- e.g. 'Essential', 'Routine'
    unit_of_measure          VARCHAR(50)                    -- e.g. 'tablet', 'vial', 'kit'
);

-- ============================================================
-- FACILITY_COMMODITY_READINESS
-- Grain: one row = the stock/readiness status of one commodity
-- at one facility, as observed at the time of the SPA 2010 survey.
-- This is a SNAPSHOT, not a time series (contrast with inventory_daily).
-- ============================================================
CREATE TABLE facility_commodity_readiness (
    facility_id         INTEGER NOT NULL REFERENCES facilities(facility_id),
    commodity_id         INTEGER NOT NULL REFERENCES commodities(commodity_id),
    stocked_status         VARCHAR(100),                  -- e.g. 'Available', 'Not Stocked'
    survey_year             INTEGER NOT NULL DEFAULT 2010,
    PRIMARY KEY (facility_id, commodity_id)                -- composite key: one status per facility+commodity
);

-- ============================================================
-- INVENTORY_DAILY
-- Grain: one row = the recorded stock movement and resulting stock
-- position of one commodity, at one facility, on one day.
-- This is SYNTHETIC data (SPA has no daily time series).
-- ============================================================
CREATE TABLE inventory_daily (
    facility_id          INTEGER NOT NULL REFERENCES facilities(facility_id),
    commodity_id          INTEGER NOT NULL REFERENCES commodities(commodity_id),
    inventory_date          DATE NOT NULL,
    opening_stock            INTEGER NOT NULL,             -- stock at start of day
    quantity_received          INTEGER NOT NULL DEFAULT 0,  -- deliveries received that day
    quantity_consumed          INTEGER NOT NULL DEFAULT 0,  -- consumption that day
    quantity_adjusted          INTEGER NOT NULL DEFAULT 0,  -- damage/loss/correction (+/-)
    closing_stock             INTEGER NOT NULL,             -- stock at end of day
    PRIMARY KEY (facility_id, commodity_id, inventory_date)  -- one record per facility+commodity+day
);