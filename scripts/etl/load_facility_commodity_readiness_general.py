# ~/supply-chain-platform/scripts/etl/load_facility_commodity_readiness_general.py
#
# Loads REAL facility_commodity_readiness data from the Kenya 2010 DHS
# SPA Facility Recode - General medication block (u403a_##/u403b_##
# name-value pairs, alphabetized by drug name).
#
# Only 1 of the 16 "letter A" slots is usable for our curated list:
#   u403b_01 -> Paracetamol 500mg (u403a_01 = "acetaminophen/paracetamol")
#
# u403a_07 ("amoxicillin (amoxil)") DOES match our curated Amoxicillin
# 500mg by NAME, but its paired availability column (u403b_07) contains
# ONLY "data not collected"/NaN for all 695 facilities - DHS recorded
# the drug's existence in the questionnaire structure but collected no
# actual availability data for it. This is a genuine, documented real-
# data gap, not a matching failure - Amoxicillin is deliberately
# excluded from this load.
#
# ORS (our third curated General commodity) is not in this block at
# all - DHS records it in a differently-structured child-services exam
# checklist (u264xe/u264xg), which uses yet another pattern. Given the
# real-data value already extracted from this dataset, ORS is treated
# as a documented synthetic-only gap rather than pursued further.

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

DHS_COLUMN_TO_COMMODITY = {
    "u403b_01": "Paracetamol 500mg",
}

# Same label scheme as the malaria block, plus a "9.0" sentinel value
# observed in this column (a DHS missing/don't-know numeric code that
# didn't receive a text label) and the CORRECTLY spelled "available"
# variant (the malaria column had a DHS typo, "availaible" - this one
# doesn't).
def decode_availability(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()

    status_map = {
        "all valid": "Available",
        "at least one valid": "Available",
        "available but none valid": "Not Stocked",
        "never available": "Not Stocked",
        "not available today/don't know": None,
        "reported available, not seen": "Reported Only",   # correct spelling
        "reported availaible, not seen": "Reported Only",  # DHS typo variant, kept defensively
        "9.0": None,  # DHS missing/don't-know numeric sentinel
    }
    return status_map.get(text, None)

# ------------------------------------------------------------------
# STEP 1: Read the Facility Recode with value labels applied.
# ------------------------------------------------------------------
columns_needed = ["v004"] + list(DHS_COLUMN_TO_COMMODITY.keys())
df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=True, columns=columns_needed)
df = df.rename(columns={"v004": "facility_num"})

print(f"Loaded {len(df)} facility rows for general medication readiness mapping")

for col in DHS_COLUMN_TO_COMMODITY:
    print(f"{col} unique values:", df[col].unique())
print()

# ------------------------------------------------------------------
# STEP 2: Connect to Postgres, build lookup tables.
# ------------------------------------------------------------------
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT facility_id, facility_name FROM facilities;")
facility_id_lookup = {name: fid for fid, name in cur.fetchall()}

cur.execute("SELECT commodity_id, commodity_name FROM commodities;")
commodity_id_lookup = {name: cid for cid, name in cur.fetchall()}

general_commodity_ids = tuple(
    commodity_id_lookup[name] for name in DHS_COLUMN_TO_COMMODITY.values()
)
cur.execute(
    "DELETE FROM facility_commodity_readiness WHERE commodity_id IN %s;",
    (general_commodity_ids,)
)
print("Cleared any existing readiness data for these general commodities.")

# ------------------------------------------------------------------
# STEP 3: Insert one row per (facility, mapped commodity) where DHS
# recorded a usable value.
# ------------------------------------------------------------------
insert_count = 0
skipped_no_facility = 0
skipped_no_value = 0

for _, row in df.iterrows():
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