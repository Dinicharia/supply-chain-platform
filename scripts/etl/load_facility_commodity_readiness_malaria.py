# ~/supply-chain-platform/scripts/etl/load_facility_commodity_readiness_malaria.py
#
# Loads REAL facility_commodity_readiness data from the Kenya 2010 DHS
# SPA Facility Recode - Malaria block (u422a_##/u422b_## name-value pairs).
#
# u422a_## slots are FIXED-POSITION (confirmed via exploration script):
# every facility's slot 2 is always "artemether-lumefantrine (coartem)",
# slot 3 is always "sulfadoxine+pyrimethamine", etc. - so we can map
# columns directly rather than doing dynamic per-row name matching.
#
# Only 2 of 12 antimalarial slots match our curated 16 commodities:
#   u422a_02 -> Artemether/Lumefantrine 20/120mg
#   u422a_03 -> Sulphadoxine/Pyrimethamine 500/25mg
# The rest (quinine, chloroquine, amodiaquine, oral artesunate, etc.)
# are real DHS data but not in our curated commodity list - deliberately
# skipped, consistent with the scope decision documented in Phase 3.

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

# Maps DHS availability column -> our commodity_name.
# Uses convert_categoricals=True, so these columns come through as
# readable text (e.g. "all valid", "never available") rather than
# numeric codes.
DHS_COLUMN_TO_COMMODITY = {
    "u422b_02": "Artemether/Lumefantrine 20/120mg",
    "u422b_03": "Sulphadoxine/Pyrimethamine 500/25mg",
}

# Converts DHS's text-labeled availability value into our simplified
# stocked_status. Uses EXPLICIT exact-label matching (not substring
# guessing) since we've now observed the full, real set of labels for
# these columns via exploration. Substring matching previously
# misclassified "never available" as Available, and "reported...not
# seen" as Not Stocked - both fixed here.
def decode_availability(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()

    status_map = {
        "all valid": "Available",
        "at least one valid": "Available",
        "available but none valid": "Not Stocked",  # stock present but unusable = effectively not stocked
        "never available": "Not Stocked",
        "not available today/don't know": None,      # genuinely ambiguous - treated as missing, not guessed
        "reported availaible, not seen": "Reported Only",  # NOTE: "availaible" is DHS's own typo, kept as-is
    }
    return status_map.get(text, None)

# ------------------------------------------------------------------
# STEP 1: Read the Facility Recode with value labels applied, so we
# can see and decode the actual text of the availability columns.
# ------------------------------------------------------------------
columns_needed = ["v004"] + list(DHS_COLUMN_TO_COMMODITY.keys())
df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=True, columns=columns_needed)
df = df.rename(columns={"v004": "facility_num"})

# NOTE: do NOT rely on df["facility_num"] type inside iterrows() later -
# iterrows() can silently upcast to float if other columns have missing
# values (this bit us in the Family Planning script). We cast at point
# of use instead.

print(f"Loaded {len(df)} facility rows for malaria readiness mapping")

# Quick visibility check on what the raw availability labels actually
# look like, before trusting decode_availability() on the full dataset.
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

# NOTE: this DELETE only clears rows for commodities we're about to
# reload, not the whole table - otherwise we'd wipe out the DMPA-IM
# rows already loaded from the Family Planning script.
malaria_commodity_ids = tuple(
    commodity_id_lookup[name] for name in DHS_COLUMN_TO_COMMODITY.values()
)
cur.execute(
    "DELETE FROM facility_commodity_readiness WHERE commodity_id IN %s;",
    (malaria_commodity_ids,)
)
print("Cleared any existing readiness data for these 2 malaria commodities.")

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