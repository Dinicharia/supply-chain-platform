# ~/supply-chain-platform/scripts/etl/load_facility_commodity_readiness_malaria.py
#
# Loads REAL facility_commodity_readiness data from the Kenya 2010 DHS
# SPA Facility Recode - Malaria block (u422a_##/u422b_## name-value
# pairs). See header comments in original version (Phase 4) for full
# DHS column mapping rationale.
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
    "u422b_02": "Artemether/Lumefantrine 20/120mg",
    "u422b_03": "Sulphadoxine/Pyrimethamine 500/25mg",
}


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
        "reported availaible, not seen": "Reported Only",  # DHS's own typo, kept as-is
    }
    return status_map.get(text, None)


def run_readiness_load_malaria():
    """
    Loads real facility_commodity_readiness data for 2 antimalarial
    commodities from the DHS Malaria block. Clears only rows for these
    commodities before reloading.
    """
    columns_needed = ["v004"] + list(DHS_COLUMN_TO_COMMODITY.keys())
    df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=True, columns=columns_needed)
    df = df.rename(columns={"v004": "facility_num"})

    print(f"Loaded {len(df)} facility rows for malaria readiness mapping")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT facility_id, facility_name FROM facilities;")
    facility_id_lookup = {name: fid for fid, name in cur.fetchall()}

    cur.execute("SELECT commodity_id, commodity_name FROM commodities;")
    commodity_id_lookup = {name: cid for cid, name in cur.fetchall()}

    malaria_commodity_ids = tuple(
        commodity_id_lookup[name] for name in DHS_COLUMN_TO_COMMODITY.values()
    )
    cur.execute(
        "DELETE FROM facility_commodity_readiness WHERE commodity_id IN %s;",
        (malaria_commodity_ids,)
    )

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
    run_readiness_load_malaria()