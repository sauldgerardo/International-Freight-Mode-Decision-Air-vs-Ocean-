# International-Freight-Mode-Decision-Air-vs-Ocean-
International Freight Mode Decision (Air vs Ocean) — analytics-heavy resume project.

What it does
- Downloads real ocean spot-rate data (BTS Excel)
- Computes air chargeable weight (actual vs volumetric)
- Estimates air cost via a documented rate-card assumption
- Estimates ocean cost using real $/40ft time series for Shanghai -> Los Angeles (and optional reverse)
- Outputs shipment-level recommendations + sensitivity features to CSV

Sources
- BTS Ocean Rates Excel (direct): https://www.bts.gov/sites/bts.dot.gov/files/2025-04/F4_23_Ocean_rates_v3.xlsx
- BTS Ocean Rates page: https://www.bts.gov/browse-statistical-products-and-data/info-gallery/freight-rates-dollars-40-foot-container-east
- Chargeable weight formulas/rules (Maersk): https://www.maersk.com/logistics-explained/transportation-and-freight/2025/03/10/air-cargo-chargeable-weight
"""
