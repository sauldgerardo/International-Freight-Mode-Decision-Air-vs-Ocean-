# International Freight Mode Decision (Air vs Ocean)

A Python analytics project that recommends **AIR vs OCEAN** for international shipments by combining:
- **Air chargeable weight** (actual vs volumetric), and
- Real **ocean spot-rate time series** (USD per 40-foot container) from the U.S. DOT Bureau of Transportation Statistics (BTS).

## What This Project Does

- Downloads BTS ocean spot-rate data (Shanghai ↔ Los Angeles)
- Generates synthetic shipment records with dimensions, pieces, and actual weight
- Computes:
  - **Volumetric weight (kg)** = (L × W × H) / 6000 using cm (air freight convention)
  - **Chargeable weight (kg)** = max(actual weight, volumetric weight)
- Estimates air cost using a documented rate-card assumption
- Estimates ocean cost by allocating $/40ft container cost using a simple utilization factor
- Outputs `data/outputs/mode_decisions_output.csv` with recommendations and analytics features (e.g., packaging sensitivity)

## Chargeable Weight Formula

Air freight billing uses **chargeable weight**, which is the higher of:
- **Actual weight** (kg), or  
- **Volumetric weight** (kg) = (Length × Width × Height) / 6000

This ensures carriers are compensated for both heavy and bulky shipments. The 6000 divisor is the standard metric convention.

**Reference:** Maersk explains volumetric weight with the 6000 divisor (cm/kg) and that billing uses the higher of actual vs volumetric weight:  
[https://www.maersk.com/logistics-explained/transportation-and-freight/2025/03/10/air-cargo-chargeable-weight](https://www.maersk.com/logistics-explained/transportation-and-freight/2025/03/10/air-cargo-chargeable-weight)

## Data Sources

**BTS Ocean Spot Rates:**
- **Page:** [https://www.bts.gov/browse-statistical-products-and-data/info-gallery/freight-rates-dollars-40-foot-container-east](https://www.bts.gov/browse-statistical-products-and-data/info-gallery/freight-rates-dollars-40-foot-container-east)
- **Direct Excel:** [https://www.bts.gov/sites/bts.dot.gov/files/2025-04/F4_23_Ocean_rates_v3.xlsx](https://www.bts.gov/sites/bts.dot.gov/files/2025-04/F4_23_Ocean_rates_v3.xlsx)

## How to Run

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script:**
   ```bash
   python src/freight_mode_decision.py
   ```

4. **View output:**
   ```
   data/outputs/mode_decisions_output.csv
   ```

## Key Assumptions

All assumptions are documented in the code for transparency:

- **Air Transit Time:** 3 days (door-to-door)
- **Ocean Transit Time:** 25 days (door-to-door)  
- **Air Rate Card:** $6.50 USD per chargeable kg, with $120 minimum charge
- **Ocean Cost Allocation:** Container cost allocated by utilization factor (default 15% = proxy for LCL/shared container)
- **Volumetric Weight Divisor:** 6000 (standard cm³/kg for air freight)

## Project Structure

```
International-Freight-Mode-Decision-Air-vs-Ocean-/
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore patterns
├── PROMPTS.md                      # Prompt engineering log
├── src/
│   └── freight_mode_decision.py   # Main Python script
└── data/
    └── outputs/
        └── mode_decisions_output.csv  # Generated recommendations
```

## Output CSV Columns

The generated CSV includes:
- Shipment details (ID, date, dims, weight, SLA)
- Computed weights (volumetric, chargeable)
- Cost estimates (air, ocean)
- Transit times and SLA flags
- **Recommended mode** (AIR or OCEAN)
- Analytics features:
  - Packaging sensitivity (10% dimension reduction impact)
  - Cost delta (air - ocean)
  - Cheaper mode

## Analytics Features

This project goes beyond simple cost comparison by including:

1. **Packaging Sensitivity Analysis:** Shows how reducing one dimension by 10% affects chargeable weight and air cost
2. **Break-even Metrics:** Calculates cost difference (Air - Ocean) per shipment
3. **SLA Compliance:** Tracks which modes meet transit requirements
4. **Mode Summary:** Terminal output shows shipment counts, average costs, and SLA compliance rates by recommended mode
