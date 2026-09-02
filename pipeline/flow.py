# ~/supply-chain-platform/pipeline/flow.py
#
# Prefect orchestration for the full data pipeline: loads real DHS
# facility/commodity-readiness data, computes facility-commodity stock
# assignments, then generates synthetic inventory/orders/shipments -
# in the correct dependency order, with automatic retries on failure.
#
# Run with: python pipeline/flow.py

from prefect import flow, task

# Import the actual work from our existing, already-tested scripts.
# This keeps "the work" (in scripts/) separate from "the orchestration
# of the work" (here) - a standard, professional pattern.
import sys
import os

# Ensure scripts/ is importable regardless of where this file is run from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.etl.load_facilities import run_facility_load
from scripts.etl.load_facility_commodity_readiness import run_readiness_load_family_planning
from scripts.etl.load_facility_commodity_readiness_malaria import run_readiness_load_malaria
from scripts.etl.load_facility_commodity_readiness_general import run_readiness_load_general
from scripts.etl.generate_facility_commodity_assignment import run_assignment_generation
from scripts.simulation.generate_inventory_daily import run_inventory_simulation
from scripts.simulation.generate_shipments import run_shipment_generation


# Each @task wraps one existing function. retries=2 means: if a task
# fails (e.g. Docker was momentarily down, as actually happened to us
# in Phase 4), Prefect automatically tries again up to 2 more times
# before giving up, with a short delay between attempts.
@task(retries=2, retry_delay_seconds=10)
def task_load_facilities():
    run_facility_load()


@task(retries=2, retry_delay_seconds=10)
def task_load_readiness_family_planning():
    run_readiness_load_family_planning()


@task(retries=2, retry_delay_seconds=10)
def task_load_readiness_malaria():
    run_readiness_load_malaria()


@task(retries=2, retry_delay_seconds=10)
def task_load_readiness_general():
    run_readiness_load_general()


@task(retries=2, retry_delay_seconds=10)
def task_generate_assignment():
    run_assignment_generation()


@task(retries=1, retry_delay_seconds=30)
def task_generate_inventory():
    run_inventory_simulation()


@task(retries=1, retry_delay_seconds=30)
def task_generate_shipments():
    run_shipment_generation()


@flow(name="supply-chain-data-pipeline")
def data_pipeline():
    """
    Full pipeline, in dependency order:
      1. Load real facilities (must happen before anything referencing
         facility_id)
      2. Load real facility_commodity_readiness (3 sub-loads, order
         doesn't matter between them - each only touches its own
         commodities)
      3. Generate facility_commodity_stock_assignment (depends on
         facilities + commodities existing)
      4. Generate synthetic inventory_daily + orders (depends on
         assignment existing)
      5. Generate synthetic shipments (depends on orders existing)
    """
    # Step 1: facilities must load first - everything else references facility_id.
    task_load_facilities()

    # Step 2: readiness loads - each is independent of the others, but
    # all depend on facilities already being loaded (Step 1).
    task_load_readiness_family_planning()
    task_load_readiness_malaria()
    task_load_readiness_general()

    # Step 3: assignment depends on facilities + commodities.
    task_generate_assignment()

    # Step 4: inventory simulation depends on assignment existing.
    task_generate_inventory()

    # Step 5: shipments depends on orders (generated in Step 4).
    task_generate_shipments()


if __name__ == "__main__":
    data_pipeline()