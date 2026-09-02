# ~/supply-chain-platform/scripts/simulation/generate_shipments.py
#
# Generates SYNTHETIC shipment records for every existing order, based
# on each order's assigned supplier's lead time and reliability_score.
# Run AFTER generate_inventory_daily.py, since it reads from orders.
#
# REFACTORED for Prefect orchestration (Phase 5).

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from datetime import timedelta, date

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "supply_chain",
    "user": "scip_user",
    "password": "scip_dev_password",
}

SIMULATION_END_DATE = date(2025, 12, 31)


def run_shipment_generation():
    """
    Generates shipment records for every order currently in the orders
    table, simulating dispatch/arrival timing based on each order's
    supplier's lead time and reliability. Clears existing shipments
    first (shipments is small relative to inventory_daily, so a plain
    DELETE is fine here - no TRUNCATE needed for performance).
    """
    rng = np.random.default_rng(seed=99)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("DELETE FROM shipments;")
    conn.commit()
    print("Cleared existing shipments data.")

    cur.execute("""
        SELECT o.order_id, o.order_date, o.quantity_ordered,
               s.average_lead_time_days, s.reliability_score
        FROM orders o
        JOIN suppliers s ON o.supplier_id = s.supplier_id;
    """)
    orders = cur.fetchall()
    print(f"Generating shipments for {len(orders)} orders")

    shipment_batch = []
    BATCH_SIZE = 50000

    def flush_batch():
        if not shipment_batch:
            return
        execute_values(
            cur,
            """
            INSERT INTO shipments
                (order_id, dispatch_date, expected_arrival_date,
                 actual_arrival_date, quantity_shipped, shipment_status)
            VALUES %s
            """,
            shipment_batch
        )
        conn.commit()
        shipment_batch.clear()

    processed = 0
    for order_id, order_date, quantity_ordered, lead_time_mean, reliability in orders:
        processed += 1
        if processed % 50000 == 0:
            print(f"  ...processed {processed}/{len(orders)} orders")

        dispatch_delay = int(rng.integers(1, 4))
        dispatch_date = order_date + timedelta(days=dispatch_delay)

        expected_arrival_date = dispatch_date + timedelta(days=int(lead_time_mean))

        delay_std = (1 - float(reliability)) * 8
        delay_days = rng.normal(loc=(1 - float(reliability)) * 5, scale=max(delay_std, 0.5))
        actual_arrival_date = expected_arrival_date + timedelta(days=int(round(delay_days)))

        if rng.random() < 0.05:
            quantity_shipped = int(quantity_ordered * rng.uniform(0.5, 0.9))
        else:
            quantity_shipped = quantity_ordered

        if actual_arrival_date <= SIMULATION_END_DATE:
            shipment_status = "Delivered"
        elif dispatch_date <= SIMULATION_END_DATE:
            shipment_status = "In Transit"
        else:
            shipment_status = "Pending"

        stored_actual_arrival = actual_arrival_date if shipment_status == "Delivered" else None

        shipment_batch.append((
            order_id, dispatch_date, expected_arrival_date,
            stored_actual_arrival, quantity_shipped, shipment_status
        ))

        if len(shipment_batch) >= BATCH_SIZE:
            flush_batch()

    flush_batch()
    print("Shipment generation complete.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_shipment_generation()