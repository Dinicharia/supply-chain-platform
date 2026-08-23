# load_facility_commodity_readiness.py
#
# Loads REAL facility_commodity_readiness data from the Kenya 2010 DHS
# SPA Facility Recode - Family Planning block (lv303_ series).
#
# Only DHS columns that map UNAMBIGUOUSLY to one of our 16 curated
# commodities (from Phase 3) are loaded. DHS columns with no match in
# our curated list, or that are ambiguous (e.g. "Implant" doesn't
# distinguish rod type), are deliberately skipped - consistent with
# the scope decision documented in Phase 3.
#
# DHS availability coding (confirmed identical across lv303a/b/d/e/g/i/j/k/l):
#   0 = No, never available            -> "Not Stocked"
#   1-4 = Various observed/valid states -> "Available"
#   5 = Reported only (not observed)    -> "Reported Only"

import pandas as pd
import psycopg2

FACILITY_RECODE_PATH = "data/raw/dhs_spa_2010/facility_recode/KEFC6AFLSR.DTA"

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

# Maps DHS column name -> our commodity_name (must match commodities.commodity_name
# exactly, as seeded in sql/seed/01_seed_commodities.sql). Only unambiguous
# matches are included - see header comment for what was excluded and why.
DHS_COLUMN_TO_COMMODITY = {
    "lv303e": "DMPA-IM Injectable Contraceptive",
}

# Converts DHS's 6-level availability code into our simplified stocked_status.
def decode_availability(code):
    if pd.isna(code):
        return None
    code = int(code)
    if code == 0:
        return "Not Stocked"
    elif code in (1, 2, 3, 4):
        return "Available"
    elif code == 5:
        return "Reported Only"
    else:
        return None  # unexpected code - treated as missing rather than guessed

# ------------------------------------------------------------------
# STEP 1: Read the Facility Recode, keeping facility_num plus the
# raw (non-labeled) codes for our mapped columns. We deliberately use
# convert_categoricals=False here since we're decoding the numeric
# codes ourselves with decode_availability(), not relying on Stata's labels.
# ------------------------------------------------------------------
columns_needed = ["v004"] + list(DHS_COLUMN_TO_COMMODITY.keys())
df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=False, columns=columns_needed)
df = df.rename(columns={"v004": "facility_num"})
df["facility_num"] = df["facility_num"].astype(int)

print(f"Loaded {len(df)} facility rows for readiness mapping")

# ------------------------------------------------------------------
# STEP 2: Connect to Postgres, build lookup tables we need for foreign keys.
# ------------------------------------------------------------------
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# facility_name follows the "Facility {facility_num}" pattern set in
# load_facilities.py, so we can look up facility_id by that same string.
cur.execute("SELECT facility_id, facility_name FROM facilities;")
facility_id_lookup = {name: fid for fid, name in cur.fetchall()}

cur.execute("SELECT commodity_id, commodity_name FROM commodities;")
commodity_id_lookup = {name: cid for cid, name in cur.fetchall()}

# Clear any prior readiness data before reloading (clean replacement,
# consistent with how we handled facilities/regions).
cur.execute("DELETE FROM facility_commodity_readiness;")
print("Cleared existing facility_commodity_readiness data.")

# ------------------------------------------------------------------
# STEP 3: Insert one row per (facility, mapped commodity) where DHS
# recorded a usable value.
# ------------------------------------------------------------------
insert_count = 0
skipped_no_facility = 0
skipped_no_value = 0

for _, row in df.iterrows():
    # iterrows() can silently upcast facility_num to float if other
    # columns in the row contain NaN (e.g. lv303e has missing values).
    # Explicitly cast back to int to match the "Facility {int}" format
    # used when facilities were originally inserted.
    facility_name = f"Facility {int(row['facility_num'])}"
    facility_id = facility_id_lookup.get(facility_name)

    if facility_id is None:
        skipped_no_facility += 1
        continue

    for dhs_col, commodity_name in DHS_COLUMN_TO_COMMODITY.items():
        stocked_status = decode_availability(row[dhs_col])
        if stocked_status is None:
            skipped_no_value += 1
            continue

        commodity_id = commodity_id_lookup[commodity_name]
        cur.execute(
            """
            INSERT INTO facility_commodity_readiness
                (facility_id, commodity_id, stocked_status, survey_year)
            VALUES (%s, %s, %s, %s);
            """,
            (facility_id, commodity_id, stocked_status, 2010)
        )
        insert_count += 1

conn.commit()

print(f"Inserted {insert_count} facility_commodity_readiness rows.")
print(f"Skipped {skipped_no_facility} rows (facility not found).")
print(f"Skipped {skipped_no_value} rows (no usable DHS value).")

cur.close()
conn.close()