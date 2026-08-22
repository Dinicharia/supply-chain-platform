# load_facilities.py
#
# Loads REAL facility data from the Kenya 2010 DHS SPA Facility Recode
# and GPS shapefile into PostgreSQL, replacing the placeholder
# regions/facilities seeded in Phase 3.
#
# Steps:
#   1. Read Facility Recode (.dta) with value labels applied
#   2. Read GPS shapefile (.shp) for coordinates
#   3. Join the two on facility ID (v004 <-> SPAFACID)
#   4. Map real facility_type -> simplified facility_tier
#   5. Delete placeholder regions/facilities
#   6. Insert real regions, then real facilities (respecting FK order)

import pandas as pd
import geopandas as gpd
import psycopg2

# --- File paths -------------------------------------------------------
FACILITY_RECODE_PATH = "data/raw/dhs_spa_2010/facility_recode/KEFC6AFLSR.DTA"
GPS_SHAPEFILE_PATH = "data/raw/dhs_spa_2010/geographic_data/KEGE6AFLSR.shp"

# --- Database connection settings (matches docker-compose.yml) --------
# NOTE: host port is 5433, not the Postgres default 5432, because a
# separate native PostgreSQL Windows service already occupies 5432 on
# this machine (see Phase 3/4 troubleshooting notes in the README).
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

# Maps each real, granular DHS facility_type to our simplified 4-tier
# model (defined in Phase 3) used for service-area/commodity-stocking
# logic. Real facility_type is preserved separately in its own column -
# this tier is an ADDITIONAL simplification, not a replacement.
TIER_MAP = {
    "national referral hospital": "County/Referral Hospital",
    "provincial hospital": "County/Referral Hospital",
    "district hospital": "Sub-County Hospital",
    "sub-district hospital": "Sub-County Hospital",
    "other hospital": "Sub-County Hospital",
    "health centre": "Health Center",
    "maternity": "Health Center",
    "stand-alone vct": "Health Center",
    "dispensary": "Dispensary",
    "clinic": "Dispensary",
}

# ------------------------------------------------------------------
# STEP 1: Read Facility Recode with value labels applied.
# convert_categoricals=True makes pandas translate numeric codes
# (e.g. v007=1) into their readable text labels (e.g. "dispensary")
# automatically, using the labels embedded in the .dta file itself.
# ------------------------------------------------------------------
facility_df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=True)
facility_df = facility_df[["v004", "v001", "v007", "v008"]].copy()
facility_df.columns = ["facility_num", "region_name", "facility_type", "managing_authority"]

# Convert categorical/Stata-labeled columns to plain strings, and
# facility_num to a plain int - avoids subtle type mismatches later
# when joining and inserting into Postgres.
facility_df["facility_num"] = facility_df["facility_num"].astype(int)
facility_df["region_name"] = facility_df["region_name"].astype(str)
facility_df["facility_type"] = facility_df["facility_type"].astype(str)
facility_df["managing_authority"] = facility_df["managing_authority"].astype(str)

# Apply the tier mapping. facility_type keeps the REAL, granular DHS
# wording; facility_tier is our simplified grouping for service-area logic.
facility_df["facility_tier"] = facility_df["facility_type"].map(TIER_MAP)

# Sanity check: every facility_type should have mapped to a tier.
# If this prints anything, our TIER_MAP is missing a category.
unmapped = facility_df[facility_df["facility_tier"].isna()]
if len(unmapped) > 0:
    print("WARNING: unmapped facility_type values found:")
    print(unmapped["facility_type"].unique())

# ------------------------------------------------------------------
# STEP 2: Read GPS shapefile, keep only what we need.
# geopandas reads .shp files into a GeoDataFrame - similar to a
# pandas DataFrame, but with an extra 'geometry' column for spatial data.
# ------------------------------------------------------------------
gps_gdf = gpd.read_file(GPS_SHAPEFILE_PATH)
gps_df = gps_gdf[["SPAFACID", "LATNUM", "LONGNUM"]].copy()
gps_df.columns = ["facility_num", "latitude", "longitude"]
gps_df["facility_num"] = gps_df["facility_num"].astype(int)

# ------------------------------------------------------------------
# STEP 3: Join Facility Recode data with GPS coordinates on facility_num.
# Using an inner join is safe here since we already verified that all
# 695 IDs match perfectly between both files (no orphans either side).
# ------------------------------------------------------------------
merged_df = facility_df.merge(gps_df, on="facility_num", how="inner")
print(f"Merged dataset: {len(merged_df)} rows (expected 695)")
print()

# ------------------------------------------------------------------
# STEP 4: Connect to Postgres and load the data.
# ------------------------------------------------------------------
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# --- Delete placeholder data first (clean replacement) ---
# Order matters: facilities references regions, so delete facilities
# before regions to respect the foreign key constraint.
cur.execute("DELETE FROM facilities;")
cur.execute("DELETE FROM regions;")
print("Deleted placeholder facilities and regions.")

# --- Insert real regions ---
# Build a region_name -> region_id lookup as we insert, since
# facilities need to reference the correct region_id (foreign key).
region_names = sorted(merged_df["region_name"].unique())
region_id_lookup = {}

for name in region_names:
    cur.execute(
        "INSERT INTO regions (country_id, region_name) VALUES (%s, %s) RETURNING region_id;",
        (1, name)  # country_id=1 is Kenya, inserted back in Phase 3
    )
    region_id_lookup[name] = cur.fetchone()[0]

print(f"Inserted {len(region_id_lookup)} real regions: {list(region_id_lookup.keys())}")

# --- Insert real facilities ---
# facility_type holds the REAL, granular DHS wording (e.g. "dispensary",
# "district hospital"); facility_tier holds our simplified 4-value
# grouping used for service-area/commodity-stocking logic from Phase 3.
insert_count = 0
for _, row in merged_df.iterrows():
    cur.execute(
        """
        INSERT INTO facilities
            (region_id, facility_name, facility_type, facility_tier,
             managing_authority, latitude, longitude, survey_year)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            region_id_lookup[row["region_name"]],
            f"Facility {row['facility_num']}",  # DHS doesn't provide real facility names for privacy
            row["facility_type"],
            row["facility_tier"],
            row["managing_authority"],
            row["latitude"],
            row["longitude"],
            2010,
        )
    )
    insert_count += 1

conn.commit()
print(f"Inserted {insert_count} real facilities.")

cur.close()
conn.close()