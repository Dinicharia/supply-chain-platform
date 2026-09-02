# ~/supply-chain-platform/scripts/etl/generate_facility_commodity_assignment.py
#
# Determines which commodities each facility stocks, based on the
# facility_tier -> service_area eligibility rule designed in Phase 3.
# A facility stocks a commodity only if the commodity's service_area
# is among the service areas that facility's tier offers.
#
# This is a business-rule/structural computation (not randomness) -
# every facility of a given tier gets the identical set of eligible
# commodities. This table becomes the backbone for the synthetic
# inventory_daily simulation: we only simulate day-to-day stock
# movement for (facility, commodity) pairs that appear here.
#
# REFACTORED for Prefect orchestration (Phase 5): the logic that used
# to run at import time now lives inside run_assignment_generation(),
# so pipeline/flow.py can import and call it as a Prefect task. Running
# this file directly (python generate_facility_commodity_assignment.py)
# still works exactly as before, via the __main__ block at the bottom.

import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

# Facility tier -> set of service areas that tier offers.
# Matches the design decided in Phase 3.
TIER_SERVICE_AREAS = {
    "Dispensary": {"General", "Family Planning"},
    "Health Center": {"General", "Family Planning", "Malaria"},
    "Sub-County Hospital": {"General", "Family Planning", "Malaria", "TB"},
    "County/Referral Hospital": {"General", "Family Planning", "Malaria", "TB", "HIV/ART"},
}


def run_assignment_generation():
    """
    Generates facility_commodity_stock_assignment from scratch, based
    on each facility's tier and each commodity's service_area. Clears
    any existing assignment data first (deterministic computation, so
    clean replacement is safe and correct).
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Pull every real facility's tier, and every commodity's service_area.
    cur.execute("SELECT facility_id, facility_tier FROM facilities;")
    facilities = cur.fetchall()  # list of (facility_id, facility_tier)

    cur.execute("SELECT commodity_id, service_area FROM commodities;")
    commodities = cur.fetchall()  # list of (commodity_id, service_area)

    print(f"Facilities: {len(facilities)}")
    print(f"Commodities: {len(commodities)}")

    # Clear any existing assignment data before regenerating.
    cur.execute("DELETE FROM facility_commodity_stock_assignment;")

    # Build the assignment: for each facility, check each commodity's
    # service_area against that facility's tier's eligible service areas.
    insert_count = 0
    for facility_id, facility_tier in facilities:
        eligible_areas = TIER_SERVICE_AREAS.get(facility_tier)

        if eligible_areas is None:
            # Defensive check: every facility_tier value should be a
            # known key in TIER_SERVICE_AREAS. If this ever prints,
            # something upstream (e.g. the tier mapping in
            # load_facilities.py) has drifted out of sync with this
            # script's assumptions.
            print(f"WARNING: unknown facility_tier '{facility_tier}' for facility_id {facility_id}")
            continue

        for commodity_id, service_area in commodities:
            if service_area in eligible_areas:
                cur.execute(
                    """
                    INSERT INTO facility_commodity_stock_assignment (facility_id, commodity_id)
                    VALUES (%s, %s);
                    """,
                    (facility_id, commodity_id)
                )
                insert_count += 1

    conn.commit()
    print(f"Inserted {insert_count} facility-commodity assignment rows.")

    cur.close()
    conn.close()


# Allows this script to still be run directly (python generate_facility_
# commodity_assignment.py), exactly as before - unchanged behavior for
# manual/standalone use, in addition to being importable by Prefect.
if __name__ == "__main__":
    run_assignment_generation()