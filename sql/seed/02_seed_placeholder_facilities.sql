-- 02_seed_placeholder_facilities.sql
--
-- *** PLACEHOLDER DATA - NOT REAL ***
-- This file seeds FAKE facilities so we can build and test the pipeline
-- (synthetic inventory/orders/shipments generation) before real Kenya
-- SPA 2010 facility data is approved and available via DHS.
--
-- TO DO once DHS approval arrives:
--   1. Replace this file's facility rows with real SPA 2010 facilities
--   2. Re-run the synthetic data generation script against real facility_ids
--   3. Delete or archive this placeholder file
--
-- Depends on: countries, regions, facilities tables (01_create_tables.sql)

-- ============================================================
-- COUNTRY (real - just Kenya, per MVP scope)
-- ============================================================
INSERT INTO countries (country_name, iso_code) VALUES
    ('Kenya', 'KEN');

-- ============================================================
-- REGIONS (placeholder - generic region names, not real Kenya counties yet)
-- ============================================================
INSERT INTO regions (country_id, region_name) VALUES
    (1, 'Placeholder Region A'),
    (1, 'Placeholder Region B'),
    (1, 'Placeholder Region C');

-- ============================================================
-- FACILITIES (placeholder - fake facilities for pipeline testing)
-- Distribution mirrors a realistic health-system pyramid: more small
-- facilities (dispensaries) than large ones (referral hospitals).
-- GPS coordinates are rough, plausible points within Kenya's bounding
-- box, NOT real facility locations.
-- ============================================================
INSERT INTO facilities (region_id, facility_name, facility_type, managing_authority, latitude, longitude, survey_year) VALUES
    -- Dispensaries (8)
    (1, 'Placeholder Dispensary 1', 'Dispensary', 'Public', -1.2921, 36.8219, 2010),
    (1, 'Placeholder Dispensary 2', 'Dispensary', 'Public', -1.3021, 36.8319, 2010),
    (2, 'Placeholder Dispensary 3', 'Dispensary', 'Public', -0.0917, 34.7680, 2010),
    (2, 'Placeholder Dispensary 4', 'Dispensary', 'NGO', -0.1017, 34.7780, 2010),
    (3, 'Placeholder Dispensary 5', 'Dispensary', 'Public', -4.0435, 39.6682, 2010),
    (3, 'Placeholder Dispensary 6', 'Dispensary', 'Public', -4.0535, 39.6782, 2010),
    (1, 'Placeholder Dispensary 7', 'Dispensary', 'Private', -1.2821, 36.8119, 2010),
    (2, 'Placeholder Dispensary 8', 'Dispensary', 'Public', -0.0817, 34.7580, 2010),

    -- Health Centers (6)
    (1, 'Placeholder Health Center 1', 'Health Center', 'Public', -1.3121, 36.8419, 2010),
    (1, 'Placeholder Health Center 2', 'Health Center', 'Public', -1.2721, 36.8019, 2010),
    (2, 'Placeholder Health Center 3', 'Health Center', 'NGO', -0.1117, 34.7880, 2010),
    (2, 'Placeholder Health Center 4', 'Health Center', 'Public', -0.0717, 34.7480, 2010),
    (3, 'Placeholder Health Center 5', 'Health Center', 'Public', -4.0335, 39.6582, 2010),
    (3, 'Placeholder Health Center 6', 'Health Center', 'Private', -4.0635, 39.6882, 2010),

    -- Sub-County Hospitals (4)
    (1, 'Placeholder Sub-County Hospital 1', 'Sub-County Hospital', 'Public', -1.2621, 36.7919, 2010),
    (2, 'Placeholder Sub-County Hospital 2', 'Sub-County Hospital', 'Public', -0.1217, 34.7980, 2010),
    (3, 'Placeholder Sub-County Hospital 3', 'Sub-County Hospital', 'Public', -4.0235, 39.6482, 2010),
    (1, 'Placeholder Sub-County Hospital 4', 'Sub-County Hospital', 'NGO', -1.3221, 36.8519, 2010),

    -- County/Referral Hospitals (2)
    (1, 'Placeholder County Hospital 1', 'County/Referral Hospital', 'Public', -1.2500, 36.8000, 2010),
    (2, 'Placeholder County Hospital 2', 'County/Referral Hospital', 'Public', -0.0600, 34.7400, 2010);