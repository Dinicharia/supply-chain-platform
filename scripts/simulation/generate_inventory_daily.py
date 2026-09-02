# ~/supply-chain-platform/scripts/simulation/generate_inventory_daily.py
#
# Generates SYNTHETIC daily inventory data for all facility-commodity
# pairs (from facility_commodity_stock_assignment) over 5 years
# (2021-2025), plus corresponding orders whenever a reorder triggers.
# See header comments in original version (Phase 4) for full mechanism
# design rationale (consumption, seasonality, reorder-point policy).
#
# REFACTORED for Prefect orchestration (Phase 5): logic now lives in
# run_inventory_simulation(). Also switched DELETE to TRUNCATE CASCADE
# for the large tables (inventory_daily has 12.6M+ rows - DELETE took
# ~25 minutes in testing; TRUNCATE is near-instant).

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from datetime import date, timedelta

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

START_DATE = date(2021, 1, 1)
NUM_DAYS = 365 * 5

TIER_MULTIPLIER = {
    "Dispensary": 1.0,
    "Health Center": 2.0,
    "Sub-County Hospital": 4.0,
    "County/Referral Hospital": 8.0,
}

BASE_CONSUMPTION = {
    "Amoxicillin 500mg": 6.0,
    "Paracetamol 500mg": 8.0,
    "ORS Sachets": 4.0,
    "Artemether/Lumefantrine 20/120mg": 5.0,
    "Sulphadoxine/Pyrimethamine 500/25mg": 3.0,
    "Injectable Artesunate 60mg": 1.0,
    "Malaria RDT (HRP2)": 4.0,
    "Long Lasting Insecticide Treated Net (LLIN)": 0.5,
    "DMPA-IM Injectable Contraceptive": 2.5,
    "Etonogestrel Implant (1 Rod)": 0.3,
    "Levonorgestrel Implant (2 Rod)": 0.3,
    "Isoniazid/Rifapentine 300/300mg": 0.5,
    "TB GeneXpert Cartridge": 0.4,
    "Dolutegravir/Lamivudine/Tenofovir DF 50/300/300mg": 1.5,
    "Emtricitabine/Tenofovir DF 200/300mg": 1.0,
    "HIV Rapid Test Kit": 2.0,
}

REORDER_POLICY = {
    "Essential": {"reorder_point_days": 10, "order_up_to_days": 30},
    "Routine": {"reorder_point_days": 20, "order_up_to_days": 45},
}


def seasonal_multiplier(current_date, service_area):
    if service_area != "Malaria":
        return 1.0
    month = current_date.month
    if month in (3, 4, 5):
        return 1.6
    elif month in (10, 11, 12):
        return 1.3
    return 1.0


def pick_supplier(managing_authority, supplier_ids_by_type, rng):
    if managing_authority == "government/ local municipality":
        weights = {"Government": 0.7, "NGO": 0.1, "Private Distributor": 0.2}
    elif managing_authority == "private for profit":
        weights = {"Government": 0.1, "NGO": 0.1, "Private Distributor": 0.8}
    else:
        weights = {"Government": 0.3, "NGO": 0.5, "Private Distributor": 0.2}

    types = list(weights.keys())
    probs = list(weights.values())
    chosen_type = rng.choice(types, p=probs)
    return int(rng.choice(supplier_ids_by_type[chosen_type]))


def run_inventory_simulation():
    """
    Simulates 5 years of daily inventory movement for every eligible
    facility-commodity pair, generating inventory_daily and orders
    records. Clears existing synthetic data first via TRUNCATE CASCADE
    (fast, unlike DELETE at this scale).
    """
    rng = np.random.default_rng(seed=42)  # fixed seed - reproducible

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT fca.facility_id, fca.commodity_id,
               f.facility_tier, f.managing_authority,
               c.commodity_name, c.service_area, c.criticality_level
        FROM facility_commodity_stock_assignment fca
        JOIN facilities f ON fca.facility_id = f.facility_id
        JOIN commodities c ON fca.commodity_id = c.commodity_id;
    """)
    pairs = cur.fetchall()
    print(f"Simulating {len(pairs)} facility-commodity pairs over {NUM_DAYS} days each")

    cur.execute("SELECT supplier_id, supplier_type FROM suppliers;")
    supplier_rows = cur.fetchall()
    supplier_ids_by_type = {}
    for sid, stype in supplier_rows:
        supplier_ids_by_type.setdefault(stype, []).append(sid)

    cur.execute("SELECT supplier_id, average_lead_time_days, reliability_score FROM suppliers;")
    supplier_info = {sid: (lead, rel) for sid, lead, rel in cur.fetchall()}

    inventory_batch = []
    orders_batch = []
    BATCH_SIZE = 50000

    def flush_inventory_batch():
        if not inventory_batch:
            return
        execute_values(
            cur,
            """
            INSERT INTO inventory_daily
                (facility_id, commodity_id, inventory_date, opening_stock,
                 quantity_received, quantity_consumed, quantity_adjusted, closing_stock)
            VALUES %s
            """,
            inventory_batch
        )
        conn.commit()
        inventory_batch.clear()

    def flush_orders_batch():
        if not orders_batch:
            return
        execute_values(
            cur,
            """
            INSERT INTO orders (facility_id, commodity_id, supplier_id, order_date, quantity_ordered)
            VALUES %s
            """,
            orders_batch
        )
        conn.commit()
        orders_batch.clear()

    # TRUNCATE CASCADE instead of DELETE: inventory_daily has millions
    # of rows, and DELETE's per-row logging made this take ~25 minutes
    # in testing. TRUNCATE deallocates instantly. CASCADE also empties
    # shipments (references orders) and orders automatically, in the
    # correct dependency order, without us managing it manually.
    cur.execute("TRUNCATE TABLE inventory_daily, orders CASCADE;")
    conn.commit()
    print("Cleared existing synthetic inventory_daily/orders/shipments data.")

    pair_count = 0
    for facility_id, commodity_id, facility_tier, managing_authority, commodity_name, service_area, criticality in pairs:
        pair_count += 1
        if pair_count % 500 == 0:
            print(f"  ...simulated {pair_count}/{len(pairs)} pairs")

        tier_mult = TIER_MULTIPLIER.get(facility_tier, 1.0)
        base_rate = BASE_CONSUMPTION.get(commodity_name, 2.0)
        avg_daily_consumption = base_rate * tier_mult

        policy = REORDER_POLICY.get(criticality, REORDER_POLICY["Routine"])
        reorder_point = avg_daily_consumption * policy["reorder_point_days"]
        order_up_to = avg_daily_consumption * policy["order_up_to_days"]

        supplier_id = pick_supplier(managing_authority, supplier_ids_by_type, rng)
        lead_time_mean, reliability = supplier_info[supplier_id]

        closing_stock = order_up_to
        pending_deliveries = {}
        current_date = START_DATE

        for _ in range(NUM_DAYS):
            opening_stock = closing_stock

            daily_mult = seasonal_multiplier(current_date, service_area)
            expected_consumption = avg_daily_consumption * daily_mult
            quantity_consumed = rng.poisson(lam=max(expected_consumption, 0.05))

            quantity_received = pending_deliveries.pop(current_date, 0)
            quantity_adjusted = 0

            available = opening_stock + quantity_received + quantity_adjusted
            quantity_consumed = min(quantity_consumed, available)
            closing_stock = available - quantity_consumed

            inventory_batch.append((
                facility_id, commodity_id, current_date,
                opening_stock, quantity_received, quantity_consumed,
                quantity_adjusted, closing_stock
            ))

            if closing_stock < reorder_point and len(pending_deliveries) == 0:
                reliability_penalty = (1 - reliability) * 10
                lead_time = max(1, int(rng.normal(lead_time_mean + reliability_penalty, 3)))
                delivery_date = current_date + timedelta(days=lead_time)
                pending_deliveries[delivery_date] = order_up_to

                orders_batch.append((
                    facility_id, commodity_id, supplier_id, current_date, int(order_up_to)
                ))

            current_date += timedelta(days=1)

            if len(inventory_batch) >= BATCH_SIZE:
                flush_inventory_batch()
            if len(orders_batch) >= BATCH_SIZE:
                flush_orders_batch()

    flush_inventory_batch()
    flush_orders_batch()

    print("Simulation complete.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_inventory_simulation()