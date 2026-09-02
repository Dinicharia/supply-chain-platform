# ~/supply-chain-platform/scripts/etl/load_facility_commodity_readiness.py
#
# Loads REAL facility_commodity_readiness data from the Kenya 2010 DHS
# SPA Facility Recode - Family Planning block (lv303_ series).
# See header comments in original version (Phase 4) for full DHS
# column mapping rationale.
#
# REFACTORED for Prefect orchestration (Phase 5).

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
    "lv303e": "DMPA-IM Injectable Contraceptive",
}


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
        return None


def run_readiness_load_family_planning():
    """
    Loads real facility_commodity_readiness data for DMPA-IM from the
    DHS Family Planning block. Clears only rows for this commodity
    before reloading (not the whole table), so it can run alongside
    the malaria/general readiness scripts without wiping their data.
    """
    columns_needed = ["v004"] + list(DHS_COLUMN_TO_COMMODITY.keys())
    df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=False, columns=columns_needed)
    df = df.rename(columns={"v004": "facility_num"})
    df["facility_num"] = df["facility_num"].astype(int)

    print(f"Loaded {len(df)} facility rows for readiness mapping")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT facility_id, facility_name FROM facilities;")
    facility_id_lookup = {name: fid for fid, name in cur.fetchall()}

    cur.execute("SELECT commodity_id, commodity_name FROM commodities;")
    commodity_id_lookup = {name: cid for cid, name in cur.fetchall()}

    # TRUNCATE requires a whole-table operation, but we only want to
    # clear THIS script's commodities (not malaria/general's rows too),
    # so we use a targeted DELETE here instead - table is small (a few
    # thousand rows), so DELETE's overhead is negligible at this scale.
    # (Contrast with inventory_daily, where TRUNCATE was necessary due
    # to its much larger size.)
    commodity_ids = tuple(commodity_id_lookup[name] for name in DHS_COLUMN_TO_COMMODITY.values())
    cur.execute("DELETE FROM facility_commodity_readiness WHERE commodity_id IN %s;", (commodity_ids,))

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


if __name__ == "__main__":
    run_readiness_load_family_planning()