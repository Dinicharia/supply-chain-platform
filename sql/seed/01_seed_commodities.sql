-- 01_seed_commodities.sql
-- Seeds the commodities table with a curated, representative subset of
-- real commodities from Kenya's official "List of Health Products and
-- Technologies" (KEMSA/MOH), filtered to facility-dispensed items only
-- (excludes lab reagents, equipment, spare parts, and PPE - see project
-- README for documented scope decisions).
--
-- This data is REAL (sourced from official MOH commodity list), unlike
-- inventory_daily/orders/shipments which will be synthetically generated.

INSERT INTO commodities (commodity_name, category, service_area, criticality_level, unit_of_measure) VALUES
    ('Dolutegravir/Lamivudine/Tenofovir DF 50/300/300mg', 'ARV', 'HIV/ART', 'Essential', 'tablet'),
    ('Emtricitabine/Tenofovir DF 200/300mg', 'ARV', 'HIV/ART', 'Essential', 'tablet'),
    ('HIV Rapid Test Kit', 'Diagnostic', 'HIV/ART', 'Essential', 'kit'),
    ('Isoniazid/Rifapentine 300/300mg', 'TB Prevention', 'TB', 'Essential', 'tablet'),
    ('TB GeneXpert Cartridge', 'Diagnostic', 'TB', 'Essential', 'cartridge'),
    ('Sulphadoxine/Pyrimethamine 500/25mg', 'Antimalarial', 'Malaria', 'Essential', 'tablet'),
    ('Artemether/Lumefantrine 20/120mg', 'Antimalarial', 'Malaria', 'Essential', 'tablet'),
    ('Injectable Artesunate 60mg', 'Antimalarial', 'Malaria', 'Essential', 'vial'),
    ('Malaria RDT (HRP2)', 'Diagnostic', 'Malaria', 'Essential', 'kit'),
    ('Long Lasting Insecticide Treated Net (LLIN)', 'Prevention', 'Malaria', 'Routine', 'unit'),
    ('DMPA-IM Injectable Contraceptive', 'Contraceptive', 'Family Planning', 'Essential', 'vial'),
    ('Etonogestrel Implant (1 Rod)', 'Contraceptive', 'Family Planning', 'Essential', 'unit'),
    ('Levonorgestrel Implant (2 Rod)', 'Contraceptive', 'Family Planning', 'Essential', 'unit'),
    ('Amoxicillin 500mg', 'Antibiotic', 'General', 'Essential', 'tablet'),
    ('Paracetamol 500mg', 'Analgesic', 'General', 'Routine', 'tablet'),
    ('ORS Sachets', 'Rehydration', 'General', 'Essential', 'sachet');