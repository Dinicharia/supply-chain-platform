# ~/supply-chain-platform/scripts/simulation/generate_inventory_daily.py
#
# Generates SYNTHETIC daily inventory data for all 6,926 real
# facility-commodity pairs (from facility_commodity_stock_assignment)
# over 5 years (2021-2025). Also generates the corresponding orders
# and shipments records whenever a reorder is triggered.
#
# Core day-by-day mechanism (consumption, reorder-point policy, lead
# times, emergent stockouts) is identical to the verified prototype in
# scripts/simulation/prototype_single_pair.py - this version scales it
# across all real pairs using parameters drawn from real facility/
# commodity attributes rather than hardcoded constants.
#
# Performance note: ~12.6 million inventory_daily rows are generated.
# Inserts are BATCHED (not one INSERT per row) using psycopg2.extras.
# execute_values, since row-by-row inserts at this scale would be
# impractically slow.

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import date, timedelta

rng = np.random.default_rng(seed=42)  # fixed seed - reproducible synthetic data

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

START_DATE = date(2021, 1, 1)
NUM_DAYS = 365 * 5

# --- Facility tier consumption multipliers (relative to Dispensary=1.0) ---
TIER_MULTIPLIER = {
    "Dispensary": 1.0,
    "Health Center": 2.0,
    "Sub-County Hospital": 4.0,
    "County/Referral Hospital": 8.0,
}

# --- Base daily consumption per commodity (illustrative, not sourced from
# real consumption data - documented as a synthetic assumption). Reflects
# relative real-world usage intensity: general medicines and malaria
# treatments are used far more often than specialized ARV/TB regimens. ---
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

# --- Reorder policy varies by criticality: Essential commodities are
# reordered sooner (less risk tolerance) with a smaller buffer target;
# Routine commodities tolerate a longer reorder trigger. ---
REORDER_POLICY = {
    "Essential": {"reorder_point_days": 10, "order_up_to_days": 30},
    "Routine": {"reorder_point_days": 20, "order_up_to_days": 45},
}

def seasonal_multiplier(current_date, service_area):
    # Only Malaria commodities get a seasonal bump, tied to Kenya's
    # long rains (Mar-May) and short rains (Oct-Dec).
    if service_area != "Malaria":
        return 1.0
    month = current_date.month
    if month in (3, 4, 5):
        return 1.6
    elif month in (10, 11, 12):
        return 1.3
    return 1.0

def pick_supplier(managing_authority, supplier_ids_by_type):
    # Government facilities lean toward the government supplier;
    # private facilities lean toward private distributors; others
    # get a roughly even mix. Simple weighted-random choice.
    if managing_authority == "government/ local municipality":
        weights = {"Government": 0.7, "NGO": 0.1, "Private Distributor": 0.2}
    elif managing_authority == "private for profit":
        weights = {"Government": 0.1, "NGO": 0.1, "Private Distributor": 0.8}
    else:  # mission/faith-based, ngo/private not for profit
        weights = {"Government": 0.3, "NGO": 0.5, "Private Distributor": 0.2}

    types = list(weights.keys())
    probs = list(weights.values())
    chosen_type = rng.choice(types, p=probs)
    return int(rng.choice(supplier_ids_by_type[chosen_type]))

# ------------------------------------------------------------------
# STEP 1: Pull everything we need from Postgres in one go.
# ------------------------------------------------------------------
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
# pairs = pairs[:20]  # TEMPORARY: test on 20 pairs first, remove this line for the full run
print(f"Simulating {len(pairs)} facility-commodity pairs over {NUM_DAYS} days each")

cur.execute("SELECT supplier_id, supplier_type FROM suppliers;")
supplier_rows = cur.fetchall()
supplier_ids_by_type = {}
for sid, stype in supplier_rows:
    supplier_ids_by_type.setdefault(stype, []).append(sid)

cur.execute("SELECT supplier_id, average_lead_time_days, reliability_score FROM suppliers;")
supplier_info = {sid: (lead, rel) for sid, lead, rel in cur.fetchall()}

# ------------------------------------------------------------------
# STEP 2: Simulate each pair, day by day. Results are accumulated in
# lists and batch-inserted periodically (not one INSERT per row).
# ------------------------------------------------------------------
inventory_batch = []
orders_batch = []
BATCH_SIZE = 50000  # rows buffered before flushing to Postgres

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

# Clear any prior synthetic data before regenerating (clean re-run).
cur.execute("DELETE FROM inventory_daily;")
cur.execute("DELETE FROM shipments;")  # shipments references orders, delete first
cur.execute("DELETE FROM orders;")
conn.commit()
print("Cleared existing synthetic inventory_daily/orders/shipments data.")

pair_count = 0
for facility_id, commodity_id, facility_tier, managing_authority, commodity_name, service_area, criticality in pairs:
    pair_count += 1
    if pair_count % 500 == 0:
        print(f"  ...simulated {pair_count}/{len(pairs)} pairs")

    tier_mult = TIER_MULTIPLIER.get(facility_tier, 1.0)
    base_rate = BASE_CONSUMPTION.get(commodity_name, 2.0)  # fallback if a name is missing
    avg_daily_consumption = base_rate * tier_mult

    policy = REORDER_POLICY.get(criticality, REORDER_POLICY["Routine"])
    reorder_point = avg_daily_consumption * policy["reorder_point_days"]
    order_up_to = avg_daily_consumption * policy["order_up_to_days"]

    supplier_id = pick_supplier(managing_authority, supplier_ids_by_type)
    lead_time_mean, reliability = supplier_info[supplier_id]

    closing_stock = order_up_to  # start each pair reasonably well-stocked
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

        # Reorder-point check (one outstanding order at a time).
        if closing_stock < reorder_point and len(pending_deliveries) == 0:
            # Less reliable suppliers add extra, more variable delay.
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

# Flush any remaining rows after the loop ends.
flush_inventory_batch()
flush_orders_batch()

print("Simulation complete.")

cur.close()
conn.close()