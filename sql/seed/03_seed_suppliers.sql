-- ~/supply-chain-platform/sql/seed/03_seed_suppliers.sql
--
-- Seeds synthetic suppliers. Modeled loosely on Kenya's real health
-- supply chain structure (KEMSA as the dominant public-sector supplier,
-- plus faith-based/NGO and private channels) - names are illustrative,
-- NOT real organizations, and should be treated as synthetic.
--
-- reliability_score (0.000-1.000) and average_lead_time_days drive our
-- synthetic order/shipment simulation later: less reliable suppliers
-- have longer, more variable lead times.

INSERT INTO suppliers (supplier_name, supplier_type, average_lead_time_days, reliability_score) VALUES
    ('Central Medical Stores Authority', 'Government', 10, 0.850),
    ('Faith-Based Health Supplies Network', 'NGO', 14, 0.780),
    ('Regional Private Distributor A', 'Private Distributor', 7, 0.900),
    ('Regional Private Distributor B', 'Private Distributor', 12, 0.700),
    ('National NGO Health Logistics', 'NGO', 18, 0.650);