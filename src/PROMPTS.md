Create a polished, resume-ready GitHub repository (Python) named air-vs-ocean-freight-optimizer that compares Air vs Ocean international freight and outputs shipment-level recommendations + analytics from real BTS ocean spot-rate data and air chargeable-weight math. Use a standard, readable project structure inspired by common research/data project layouts (separate src/, data/, tests/, scripts/).
​

Repo structure (must generate all files)
text
air-vs-ocean-freight-optimizer/
  README.md
  pyproject.toml  (or requirements.txt; choose one and be consistent)
  .gitignore
  data/
    raw/          (downloaded BTS xlsx cached here)
    processed/    (generated CSV outputs here)
  src/air_ocean_optimizer/
    __init__.py
    config.py
    bts_rates.py
    shipments.py
    costing.py
    recommend.py
    reporting.py
    cli.py
  scripts/
    run_pipeline.py  (simple runner that calls the package)
  tests/
    test_costing.py
    test_recommendation.py
Keep code importable as a package under src/ (not notebooks-only).
​

Core objective
Build a reproducible pipeline that:

Downloads + caches BTS ocean spot-rate workbook: 
https://www.bts.gov/sites/bts.dot.gov/files/2025-04/F4_23_Ocean_rates_v3.xlsx
​

Extracts Shanghai ↔ Los Angeles lane rates for both directions (inbound + outbound). Prefer using query-style sheets if present (e.g., dataQuery_Outbound and dataQuery_Inbound) and filter on origin/destination text containing “Shanghai” and “Los Angeles”.
​

Generates synthetic shipments and computes both air and ocean cost estimates, then recommends the best mode subject to SLA.
​

Business logic requirements
Synthetic shipments
Generate 
n
=
500
n=500 shipments with a fixed random seed.

Required fields: shipment_id, direction (CN_TO_US or US_TO_CN), ship_date, actual_weight_kg, L_cm, W_cm, H_cm, sla_max_transit_days.

Validate: dimensions > 0, weights > 0, SLA > 0.

Air math + air costing
Volumetric weight (kg) = (LWH)/6000 using cm.

Chargeable weight = max(actual, volumetric).

Air cost = rate-card function (tiered per-kg + base fee) defined in config.py with clear assumptions.

Ocean costing (must use BTS rates)
Use BTS rate as dollars per container (prefer 40ft when available; fall back with explicit logic).

Allocate per-shipment ocean cost using container utilization:

Compute shipment CBM from dimensions.

Utilization = min(shipment_cbm / container_cbm, 1.0).

Shipment ocean cost = utilization * container_rate.

Put container_cbm and all assumptions in config.py.

Transit + recommendation
Assign configurable transit days for air and ocean.

Decision rule:

Choose lowest-cost mode that meets SLA.

If only one meets SLA, choose it.

If neither meets SLA, set recommended_mode = "NO_SLA_MODE" but still output both costs + SLA gaps.

“Stand-out” analytics
Packaging sensitivity: reduce the largest dimension by 10%, recompute chargeable weight and air cost, output deltas.

Break-even metric per shipment: air_cost_usd - ocean_cost_usd.

Print a terminal summary table: counts, % share, avg cost, total spend, % meeting SLA by mode.

Outputs (must be written)
data/processed/freight_mode_recommendations.csv with clean, analysis-ready column names.

CSV must include: computed weights, both mode costs, transit days, SLA flags, recommended mode, sensitivity deltas, and break-even.

CLI + usability
Provide python -m air_ocean_optimizer --n 500 --seed 42 --out data/processed/... via cli.py.

scripts/run_pipeline.py should run the end-to-end pipeline with sensible defaults.

README quality bar
README.md must include:

2–3 sentence project overview (resume-ready)

Data source link (BTS workbook)

How to run (create venv, install deps, run CLI)

Key assumptions (rate card, container CBM, transit days, utilization model)

Testing
Add small unit tests for:

volumetric/chargeable weight calculations

recommendation logic when SLA filters apply

Constraints

Use Python 3.11+ with pandas, numpy, requests, and openpyxl.

No paid APIs; must rely on BTS workbook + generated data only.
​
