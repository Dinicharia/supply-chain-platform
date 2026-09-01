# ~/supply-chain-platform/scripts/simulation/prototype_single_pair.py
#
# PROTOTYPE: simulates daily inventory for ONE facility+commodity pair
# over 5 years, so we can sanity-check the simulation logic on a small,
# readable scale before scaling to all 6,926 pairs. Not part of the
# final pipeline - throwaway/diagnostic, like our earlier exploration
# scripts.
#
# Simulates: daily consumption (with tier + seasonal effects + noise),
# a reorder-point policy, and supplier lead times. Stockouts are NOT
# directly generated - they emerge naturally when closing_stock hits 0
# before the next delivery arrives (avoids data leakage - see Phase 3
# notes on this exact design decision).

import numpy as np
import pandas as pd
from datetime import date, timedelta

# Reproducibility: fixed seed so results are consistent across runs -
# important for debugging, and a professional habit for any simulation.
rng = np.random.default_rng(seed=42)

# --- Simulation parameters for this single prototype pair -------------
FACILITY_TIER = "Health Center"
COMMODITY_SERVICE_AREA = "Malaria"
BASE_DAILY_CONSUMPTION = 5.0      # average units/day at a baseline (Dispensary) tier
TIER_MULTIPLIER = 2.0              # Health Center consumes ~2x a Dispensary's baseline
REORDER_POINT_DAYS = 14            # reorder when stock falls below 14 days of avg consumption
ORDER_UP_TO_DAYS = 45              # order enough to bring stock up to 45 days of avg consumption
SUPPLIER_LEAD_TIME_DAYS = 10       # average days between order and delivery
SUPPLIER_LEAD_TIME_STD = 3         # variability in lead time (std dev, for realism)
STARTING_STOCK = 150               # opening stock on day 1

START_DATE = date(2021, 1, 1)
NUM_DAYS = 365 * 5  # 5 years

# --- Seasonal multiplier: malaria consumption spikes during Kenya's --
# --- long rains (Mar-May) and short rains (Oct-Dec) -------------------
def seasonal_multiplier(current_date):
    month = current_date.month
    if month in (3, 4, 5):        # long rains
        return 1.6
    elif month in (10, 11, 12):   # short rains
        return 1.3
    else:
        return 1.0

# --- Simulation state ---------------------------------------------------
closing_stock = STARTING_STOCK
avg_daily_consumption = BASE_DAILY_CONSUMPTION * TIER_MULTIPLIER
reorder_point = avg_daily_consumption * REORDER_POINT_DAYS
order_up_to = avg_daily_consumption * ORDER_UP_TO_DAYS

pending_deliveries = {}  # maps delivery_date -> quantity, for orders in transit
records = []

current_date = START_DATE
for day_offset in range(NUM_DAYS):
    opening_stock = closing_stock

    # --- Consumption for today ---
    daily_mult = seasonal_multiplier(current_date)
    expected_consumption = avg_daily_consumption * daily_mult
    # Poisson noise: appropriate for count-like data (can't consume
    # a negative number of units, and variance scales naturally with
    # the mean - realistic for daily demand).
    quantity_consumed = rng.poisson(lam=max(expected_consumption, 0.1))

    # --- Deliveries arriving today ---
    quantity_received = pending_deliveries.pop(current_date, 0)

    # --- No manual adjustments in this simple prototype (kept at 0) ---
    quantity_adjusted = 0

    # --- Compute closing stock, but never below zero ---
    # (Consumption can't exceed what's actually available - if demand
    # exceeds stock, the facility experiences a stockout; unmet demand
    # is simply not recorded as "consumed".)
    available = opening_stock + quantity_received + quantity_adjusted
    quantity_consumed = min(quantity_consumed, available)
    closing_stock = available - quantity_consumed

    records.append({
        "date": current_date,
        "opening_stock": opening_stock,
        "quantity_received": quantity_received,
        "quantity_consumed": quantity_consumed,
        "quantity_adjusted": quantity_adjusted,
        "closing_stock": closing_stock,
    })

    # --- Reorder-point check: place a new order if stock is low, and
    # there isn't already a delivery pending (simple policy: one
    # outstanding order at a time) ---
    if closing_stock < reorder_point and len(pending_deliveries) == 0:
        lead_time = max(1, int(rng.normal(SUPPLIER_LEAD_TIME_DAYS, SUPPLIER_LEAD_TIME_STD)))
        delivery_date = current_date + timedelta(days=lead_time)
        pending_deliveries[delivery_date] = order_up_to

    current_date += timedelta(days=1)

# --- Output as a DataFrame for easy inspection ---
df = pd.DataFrame(records)

print(df.head(20))
print()
print("Summary statistics:")
print(df[["opening_stock", "quantity_received", "quantity_consumed", "closing_stock"]].describe())
print()
print(f"Number of days with closing_stock == 0 (stockout days): {(df['closing_stock'] == 0).sum()}")
print(f"Number of orders placed (deliveries scheduled): approx via received>0 count: {(df['quantity_received'] > 0).sum()}")