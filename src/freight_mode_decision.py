BTS_OCEAN_XLSX_URL = "https://www.bts.gov/sites/bts.dot.gov/files/2025-04/F4_23_Ocean_rates_v3.xlsx"

# Sheet names observed in the BTS workbook.
SHEET_INBOUND = "data_forFigureInbound"    # Shanghai -> Los Angeles
SHEET_OUTBOUND = "data_forFigureOutbound"  # Los Angeles -> Shanghai

# Column names in the figure sheets (as seen in BTS workbook dump)
COL_DATE = "Date"
COL_INBOUND_RATE = "From Central China (Shanghai) to U.S. West Coast (Los Angeles)"
COL_OUTBOUND_RATE_LA = "From U.S. West Coast (Los Angeles) to Central China (Shanghai)"

# Business assumptions (document these clearly in README)
DEFAULT_OCEAN_TRANSIT_DAYS = 25  # door-to-door is variable; keep this as an explicit assumption
DEFAULT_AIR_TRANSIT_DAYS = 3

# Air "rate card" assumption: USD per chargeable kg (you can refine later)
DEFAULT_AIR_USD_PER_CHG_KG = 6.50
DEFAULT_AIR_MIN_CHARGE_USD = 120.0

# Ocean: allocate container cost to shipment using a simple utilization factor
# If utilization=1.0, shipment "uses" a full 40ft container. If 0.1, it's 10% of container cost.
# This is a simplification to turn $/container into $/shipment; document it.
DEFAULT_CONTAINER_UTILIZATION = 0.15


# -----------------------------
# Data classes
# -----------------------------

@dataclass
class Shipment:
    shipment_id: str
    ship_date: str  # YYYY-MM-DD
    incoterm: str = "FOB"  # not used in math; left for realism

    # Dims per piece
    length_cm: float = 50.0
    width_cm: float = 40.0
    height_cm: float = 30.0

    pieces: int = 1
    actual_weight_kg: float = 20.0

    # Service requirement
    max_transit_days: int = 10

    # For ocean allocation (LCL-ish proxy)
    container_utilization: float = DEFAULT_CONTAINER_UTILIZATION

    # Lane direction:
    # "inbound" = Shanghai -> Los Angeles (uses inbound sheet)
    # "outbound" = Los Angeles -> Shanghai (uses outbound sheet)
    direction: str = "inbound"


# -----------------------------
# Download + load BTS ocean data
# -----------------------------

def download_excel(url: str, timeout_s: int = 30) -> bytes:
    r = requests.get(url, timeout=timeout_s)
    r.raise_for_status()
    return r.content


def load_bts_ocean_rates(excel_bytes: bytes) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      inbound_df: columns [date, ocean_rate_usd_per_40ft]
      outbound_df: columns [date, ocean_rate_usd_per_40ft]
    """
    with io.BytesIO(excel_bytes) as bio:
        inbound = pd.read_excel(bio, sheet_name=SHEET_INBOUND)
    with io.BytesIO(excel_bytes) as bio:
        outbound = pd.read_excel(bio, sheet_name=SHEET_OUTBOUND)

    inbound = inbound[[COL_DATE, COL_INBOUND_RATE]].rename(
        columns={COL_DATE: "date", COL_INBOUND_RATE: "ocean_rate_usd_40ft"}
    )
    outbound = outbound[[COL_DATE, COL_OUTBOUND_RATE_LA]].rename(
        columns={COL_DATE: "date", COL_OUTBOUND_RATE_LA: "ocean_rate_usd_40ft"}
    )

    inbound["date"] = pd.to_datetime(inbound["date"])
    outbound["date"] = pd.to_datetime(outbound["date"])

    inbound["ocean_rate_usd_40ft"] = pd.to_numeric(inbound["ocean_rate_usd_40ft"], errors="coerce")
    outbound["ocean_rate_usd_40ft"] = pd.to_numeric(outbound["ocean_rate_usd_40ft"], errors="coerce")

    inbound = inbound.dropna(subset=["ocean_rate_usd_40ft"]).sort_values("date").reset_index(drop=True)
    outbound = outbound.dropna(subset=["ocean_rate_usd_40ft"]).sort_values("date").reset_index(drop=True)

    return inbound, outbound


def nearest_month_rate(rates_df: pd.DataFrame, ship_date: pd.Timestamp) -> float:
    """
    BTS is monthly; pick the nearest month (or you can do ffill/bfill).
    """
    idx = (rates_df["date"] - ship_date).abs().idxmin()
    return float(rates_df.loc[idx, "ocean_rate_usd_40ft"])


# -----------------------------
# Freight math: air chargeable weight
# -----------------------------

def volumetric_weight_kg(length_cm: float, width_cm: float, height_cm: float, pieces: int = 1, divisor: float = 6000.0) -> float:
    """
    Maersk notes common metric divisor 6000 for cm/kg volumetric weight.
    volumetric_kg = (L*W*H)/divisor per piece, times pieces.
    """
    vol = (length_cm * width_cm * height_cm) / divisor
    return float(vol * pieces)


def chargeable_weight_kg(actual_weight_kg: float, vol_weight_kg: float) -> float:
    """
    Chargeable weight is the higher of actual and volumetric weight.
    """
    return float(max(actual_weight_kg, vol_weight_kg))


# -----------------------------
# Cost models
# -----------------------------

def estimate_air_cost_usd(chg_weight_kg: float, usd_per_chg_kg: float = DEFAULT_AIR_USD_PER_CHG_KG, min_charge: float = DEFAULT_AIR_MIN_CHARGE_USD) -> float:
    return float(max(min_charge, chg_weight_kg * usd_per_chg_kg))


def estimate_ocean_cost_usd(ocean_rate_usd_40ft: float, utilization: float) -> float:
    utilization = float(np.clip(utilization, 0.0, 1.0))
    return float(ocean_rate_usd_40ft * utilization)


# -----------------------------
# Decision logic (analytics-first)
# -----------------------------

def recommend_mode(air_cost: float, ocean_cost: float, air_days: int, ocean_days: int, max_days: int) -> str:
    """
    Keep it simple and explainable:
    - If only one mode meets transit constraint, pick it.
    - If both meet, pick cheaper.
    - If neither meets, pick faster (still a constraint violation; call it out in KPIs).
    """
    air_ok = air_days <= max_days
    ocean_ok = ocean_days <= max_days

    if air_ok and not ocean_ok:
        return "AIR"
    if ocean_ok and not air_ok:
        return "OCEAN"
    if air_ok and ocean_ok:
        return "AIR" if air_cost < ocean_cost else "OCEAN"
    return "AIR" if air_days < ocean_days else "OCEAN"


def build_shipments_demo(n: int = 50, seed: int = 7) -> pd.DataFrame:
    """
    Generates a realistic-ish shipment table you can replace with your own later.
    """
    rng = np.random.default_rng(seed)

    df = pd.DataFrame({
        "shipment_id": [f"S{i:04d}" for i in range(1, n + 1)],
        "ship_date": pd.to_datetime(rng.choice(pd.date_range("2022-01-01", "2024-08-01", freq="7D"), size=n)),
        "length_cm": rng.integers(20, 120, size=n),
        "width_cm": rng.integers(20, 100, size=n),
        "height_cm": rng.integers(10, 90, size=n),
        "pieces": rng.integers(1, 8, size=n),
        "actual_weight_kg": np.round(rng.uniform(5, 250, size=n), 1),
        "max_transit_days": rng.choice([5, 7, 10, 14, 21, 30], size=n, p=[0.10, 0.15, 0.25, 0.20, 0.20, 0.10]),
        "container_utilization": np.round(rng.uniform(0.03, 0.35, size=n), 3),
        "direction": rng.choice(["inbound", "outbound"], size=n, p=[0.8, 0.2]),
    })
    return df


def add_sensitivity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analytics differentiators:
    - How close is the shipment to flipping from actual-weight-priced to volume-priced?
    - What happens to chargeable weight if you reduce one dimension by 10% (packaging improvement)?
    """
    # baseline
    df["vol_weight_kg"] = df.apply(lambda r: volumetric_weight_kg(r["length_cm"], r["width_cm"], r["height_cm"], int(r["pieces"])), axis=1)
    df["chg_weight_kg"] = df.apply(lambda r: chargeable_weight_kg(float(r["actual_weight_kg"]), float(r["vol_weight_kg"])), axis=1)

    # ratio: >1 means volumetric > actual (bulky); <1 means dense (actual > volumetric)
    df["vol_to_actual_ratio"] = df["vol_weight_kg"] / df["actual_weight_kg"].replace(0, np.nan)

    # packaging improvement scenario (reduce height 10%)
    df["vol_weight_kg_pack10"] = df.apply(
        lambda r: volumetric_weight_kg(r["length_cm"], r["width_cm"], r["height_cm"] * 0.9, int(r["pieces"])),
        axis=1
    )
    df["chg_weight_kg_pack10"] = df.apply(lambda r: chargeable_weight_kg(float(r["actual_weight_kg"]), float(r["vol_weight_kg_pack10"])), axis=1)
    df["chg_weight_delta_kg_pack10"] = df["chg_weight_kg_pack10"] - df["chg_weight_kg"]

    return df


def run_pipeline(
    shipments_df: pd.DataFrame,
    air_usd_per_chg_kg: float = DEFAULT_AIR_USD_PER_CHG_KG,
    air_min_charge_usd: float = DEFAULT_AIR_MIN_CHARGE_USD,
    ocean_days: int = DEFAULT_OCEAN_TRANSIT_DAYS,
    air_days: int = DEFAULT_AIR_TRANSIT_DAYS,
) -> pd.DataFrame:
    # Load real ocean rates
    excel_bytes = download_excel(BTS_OCEAN_XLSX_URL)
    inbound_rates, outbound_rates = load_bts_ocean_rates(excel_bytes)

    df = shipments_df.copy()
    df["ship_date"] = pd.to_datetime(df["ship_date"])

    # Compute chargeable weight + sensitivity features
    df = add_sensitivity_features(df)

    # Attach ocean rate based on lane direction and ship month
    def _ocean_rate_for_row(r):
        rates = inbound_rates if r["direction"] == "inbound" else outbound_rates
        return nearest_month_rate(rates, r["ship_date"])

    df["ocean_rate_usd_40ft"] = df.apply(_ocean_rate_for_row, axis=1)

    # Cost models
    df["air_cost_usd"] = df["chg_weight_kg"].apply(lambda x: estimate_air_cost_usd(x, air_usd_per_chg_kg, air_min_charge_usd))
    df["ocean_cost_usd"] = df.apply(lambda r: estimate_ocean_cost_usd(r["ocean_rate_usd_40ft"], r["container_utilization"]), axis=1)

    # Service / decisions
    df["air_transit_days"] = air_days
    df["ocean_transit_days"] = ocean_days
    df["air_meets_sla"] = df["air_transit_days"] <= df["max_transit_days"]
    df["ocean_meets_sla"] = df["ocean_transit_days"] <= df["max_transit_days"]

    df["recommended_mode"] = df.apply(
        lambda r: recommend_mode(
            r["air_cost_usd"], r["ocean_cost_usd"], int(r["air_transit_days"]), int(r["ocean_transit_days"]), int(r["max_transit_days"])
        ),
        axis=1
    )

    # Helpful analytics columns
    df["cost_delta_air_minus_ocean_usd"] = df["air_cost_usd"] - df["ocean_cost_usd"]
    df["cheaper_mode"] = np.where(df["air_cost_usd"] < df["ocean_cost_usd"], "AIR", "OCEAN")

    # Sort for readability
    df = df.sort_values(["ship_date", "shipment_id"]).reset_index(drop=True)
    return df


def main():
    # Demo shipments; replace by reading your own CSV later
    shipments = build_shipments_demo(n=80, seed=11)

    results = run_pipeline(shipments)

    out_path = "mode_decisions_output.csv"
    results.to_csv(out_path, index=False)

    # Print a small summary
    summary = (
        results.groupby("recommended_mode")
        .agg(
            shipments=("shipment_id", "count"),
            avg_air_cost=("air_cost_usd", "mean"),
            avg_ocean_cost=("ocean_cost_usd", "mean"),
            pct_meeting_sla_air=("air_meets_sla", "mean"),
            pct_meeting_sla_ocean=("ocean_meets_sla", "mean"),
        )
        .reset_index()
    )

    print("\nWrote:", out_path)
    print("\nMode summary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
