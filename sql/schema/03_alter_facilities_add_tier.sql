-- 03_alter_facilities_add_tier.sql
-- Adds facility_tier: a simplified 4-tier classification derived from
-- the real, more granular DHS facility_type values. facility_type keeps
-- the authentic DHS wording (10 distinct types); facility_tier maps
-- each into our existing service-area/commodity-stocking logic from
-- Phase 3 (Dispensary / Health Center / Sub-County Hospital /
-- County-Referral Hospital tiers).

ALTER TABLE facilities ADD COLUMN facility_tier VARCHAR(50);