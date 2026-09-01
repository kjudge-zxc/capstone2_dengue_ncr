"""Population estimation for LGU-years without an official PSA reference point.

Two official anchors are available for every NCR LGU:

    2020 -- PSA Census of Population and Housing
    2024 -- PSA Census of Population (POPCEN)

Everything else is derived from those two anchors using a single linear growth
model:

    P(t) = P0 + (P1 - P0) * (t - t0) / (t1 - t0)

where P0, P1 are the official population figures for anchor years t0=2020 and
t1=2024. Applied to a year between the anchors (2021-2023) this is
interpolation, bounded on both sides by real data. Applied to a year beyond
the anchors (2025) this is extrapolation: the same formula, but with no second
anchor holding the estimate in check, so it simply continues the observed
2020-2024 growth rate forward by one year. The formula is identical; only the
position of t relative to [t0, t1] differs, and it is that position which
determines the status label attached to the estimate.

2024 itself is never computed -- the official POPCEN figure is used directly.

Every produced value is tagged with a status so that official, interpolated,
and extrapolated figures are never silently conflated downstream:

    official       -- 2020 and 2024, taken directly from the PSA source files
    interpolated   -- 2021, 2022, 2023 (between the two anchors)
    extrapolated   -- 2025 (beyond the last anchor; lower-confidence)
"""

import pandas as pd

from src.lgu_names import normalize_lgu_name

ANCHOR_YEAR_0 = 2020
ANCHOR_YEAR_1 = 2024
ALL_YEARS = [2021, 2022, 2023, 2024, 2025]

STATUS_OFFICIAL = "official"
STATUS_INTERPOLATED = "interpolated"
STATUS_EXTRAPOLATED = "extrapolated"


def _status_for_year(year: int) -> str:
    if year in (ANCHOR_YEAR_0, ANCHOR_YEAR_1):
        return STATUS_OFFICIAL
    if ANCHOR_YEAR_0 < year < ANCHOR_YEAR_1:
        return STATUS_INTERPOLATED
    if year > ANCHOR_YEAR_1:
        return STATUS_EXTRAPOLATED
    raise ValueError(
        f"Year {year} is before the 2020 anchor; this study's panel starts at 2021."
    )


def estimate_population(p0: float, p1: float, year: int) -> float:
    """Estimate population for `year` from the 2020 (p0) and 2024 (p1) anchors.

    Interpolates for 2021-2023, extrapolates for 2025, and returns the anchor
    value unchanged for 2020 or 2024. The same linear formula drives both
    interpolation and extrapolation; only whether `year` falls inside or
    outside [2020, 2024] differs.
    """
    if year < ANCHOR_YEAR_0:
        raise ValueError(
            f"Year {year} is before the 2020 anchor; this study's panel starts at 2021."
        )
    if year == ANCHOR_YEAR_0:
        return float(p0)
    if year == ANCHOR_YEAR_1:
        return float(p1)

    fraction = (year - ANCHOR_YEAR_0) / (ANCHOR_YEAR_1 - ANCHOR_YEAR_0)
    return p0 + (p1 - p0) * fraction


def compute_density(population: float, land_area: float) -> float:
    """Population density in persons per square kilometre."""
    if land_area <= 0:
        raise ValueError(f"Land area must be positive, got {land_area}")
    return population / land_area


def build_population_panel(pop_2020: pd.DataFrame, pop_2024: pd.DataFrame) -> pd.DataFrame:
    """Build the long-format LGU x year population/density table for 2021-2025.

    Parameters
    ----------
    pop_2020, pop_2024 : DataFrame
        The official PSA reference tables, each with columns
        "City and Municipality", "Total Population", "Land Area".

    Returns
    -------
    DataFrame with one row per LGU-year (17 x 5 = 85 rows) and columns:
        LGU, Year, Population, Land Area, Population Density, Status
    """
    p20 = pop_2020.copy()
    p24 = pop_2024.copy()
    p20["LGU"] = p20["City and Municipality"].map(normalize_lgu_name)
    p24["LGU"] = p24["City and Municipality"].map(normalize_lgu_name)

    merged = p20[["LGU", "Total Population", "Land Area"]].merge(
        p24[["LGU", "Total Population", "Land Area"]],
        on="LGU",
        suffixes=("_2020", "_2024"),
        validate="one_to_one",
    )

    # Land area is fixed and identical across both census releases; carry the 2020 figure forward as the single land-area value used for every year
    mismatched = merged[merged["Land Area_2020"] != merged["Land Area_2024"]]
    if not mismatched.empty:
        raise ValueError(
            "Land area differs between the 2020 and 2024 reference files for: "
            f"{mismatched['LGU'].tolist()}"
        )

    rows = []
    for _, r in merged.iterrows():
        land_area = r["Land Area_2020"]
        for year in ALL_YEARS:
            population = estimate_population(
                r["Total Population_2020"], r["Total Population_2024"], year
            )
            rows.append(
                {
                    "LGU": r["LGU"],
                    "Year": year,
                    "Population": population,
                    "Land Area": land_area,
                    "Population Density": compute_density(population, land_area),
                    "Status": _status_for_year(year),
                }
            )

    panel = pd.DataFrame(rows).sort_values(["LGU", "Year"]).reset_index(drop=True)
    return panel