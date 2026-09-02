# Global Health Supply Chain Risk & Stockout Prediction Platform

A portfolio project demonstrating end-to-end data engineering, machine learning, and MLOps: predicting medicine stockout risk across health facilities in Kenya.

**Status:** In development — Phase 5 (Prefect orchestration) complete. Local data platform is fully built and reproducible via a single orchestrated pipeline.

---

## Project Overview

This platform predicts stockout risk for essential medicines across health facilities, using a hybrid of real facility/commodity data (Kenya DHS Service Provision Assessment 2010) and synthetically simulated daily inventory operations. It follows a Bronze/Silver/Gold-style architecture and is being built progressively, phase by phase, as a hands-on learning project in data engineering, ML, and MLOps.

## Architecture


## Data Sources

### Real data
- **Kenya 2010 DHS Service Provision Assessment (SPA)** — Facility Recode and GPS datasets, obtained via registered DHS Program access.
  - 695 real health facilities (dispensaries, health centers, sub-county hospitals, county/referral hospitals), with GPS coordinates, managing authority, and region.
  - `facility_commodity_readiness`: real, point-in-time (2010) stock-availability data for 4 of our 16 curated commodities (DMPA-IM, Artemether/Lumefantrine, Sulphadoxine/Pyrimethamine, Paracetamol).
- **Kenya MOH "List of Health Products and Technologies"** — used to curate a representative, facility-dispensable subset of 16 real commodities across 5 service areas (General, Family Planning, Malaria, TB, HIV/ART), deliberately excluding lab reagents, equipment, and near-duplicate SKU variants to keep MVP scope disciplined.

### Documented real-data limitations
- **TB and HIV/ART commodities have zero real readiness data.** Our curated commodity list reflects *current* (2020s) Kenya MOH treatment regimens (e.g., dolutegravir-based ARVs, isoniazid/rifapentine TB prevention), which did not exist in Kenya's 2010 treatment protocols. This is a genuine temporal mismatch between a current reference list and a historical (2010) survey, not a data quality issue.
- **Amoxicillin** matches a real DHS column by name, but that column's availability data was recorded as "data not collected" for all 695 facilities — a real DHS data gap, not a matching failure.
- **ORS** is recorded in a differently-structured section of the DHS questionnaire (child-services exam checklist) than the rest of our commodities; deliberately not pursued further to keep scope disciplined.

### Synthetic data
- `suppliers`, `orders`, `shipments`, and all `inventory_daily` records are synthetically generated, **not real**.
- `inventory_daily` is generated via a day-by-day discrete-time simulation (2021-2025, 5 years) incorporating: facility-tier-based consumption multipliers, per-commodity base consumption rates, malaria seasonality (Kenya's long/short rains), a reorder-point inventory policy (varying by commodity criticality), and supplier lead-time/reliability effects.
- **Stockouts are never directly assigned** — they emerge naturally when simulated consumption outpaces simulated resupply, specifically to avoid data leakage in future ML models (a stockout label must never be traceable back to a rule that generated it directly).

## Data Model

9 core tables: `countries`, `regions`, `facilities`, `commodities`, `facility_commodity_readiness`, `facility_commodity_stock_assignment`, `inventory_daily`, `suppliers`, `orders`, `shipments`.

Facilities carry both a real, granular `facility_type` (as recorded by DHS, e.g. "dispensary", "district hospital") and a simplified `facility_tier` (4 levels: Dispensary / Health Center / Sub-County Hospital / County-Referral Hospital) used to drive service-area eligibility and consumption-scale logic.

## Tech Stack

- **Language:** Python 3.12.10 (pinned via pyenv-win)
- **Database:** PostgreSQL 16 (Docker container `supply-chain-db`, host port 5433)
- **Orchestration:** Prefect 3.x
- **Key libraries:** pandas, geopandas, numpy, psycopg2

## Running the Pipeline

Prerequisites: Docker Desktop running, Python virtual environment activated (`source .venv/Scripts/activate`), dependencies installed (`pip install -r requirements.txt`), and the Postgres container up (`docker compose up -d`).

```bash
python pipeline/flow.py
```

This runs the full pipeline end-to-end: loads real facility/commodity-readiness data from the raw DHS files, computes facility-commodity stock eligibility, and generates 5 years of synthetic daily inventory, orders, and shipments (~12.6 million inventory rows). Full local re-run takes approximately 10-15 minutes.

**Note:** raw DHS data files are not included in this repository (restricted-access data under DHS Program usage terms) and must be obtained separately via [dhsprogram.com](https://dhsprogram.com) registration.

## Project Phases

- [x] Phase 0 — Project Orientation
- [x] Phase 1 — Windows Development Environment
- [x] Phase 2 — Data Discovery
- [x] Phase 3 — Data Modeling
- [x] Phase 4 — Local Data Platform
- [x] Phase 5 — Prefect Orchestration
- [ ] Phase 6 — Analytics
- [ ] Phase 7 — Stockout ML
- [ ] Phase 8 — Forecasting
- [ ] Phase 9 — Risk & Resupply
- [ ] Phase 10 — ML API
- [ ] Phase 11 — Docker (containerizing the app itself)
- [ ] Phase 12-14 — AWS Fundamentals, Data Platform, ML Deployment
- [ ] Phase 15 — Monitoring
- [ ] Phase 16 — CI/CD
- [ ] Phase 17 — Scalability Testing
- [ ] Phase 18 — Final Dashboard
- [ ] Phase 19 — Documentation (polish pass)
- [ ] Phase 20 — Portfolio & Interview Preparation