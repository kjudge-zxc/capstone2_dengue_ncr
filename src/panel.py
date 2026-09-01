"""Build the merged 85-row LGU-year analytical panel.

Combines the wide-format FOI dengue case counts (one row per LGU, one column
per year) with the long-format population/density panel from
`src.population.build_population_panel`, producing a single long-format table:

    LGU, Year, Dengue Cases, Population, Land Area, Population Density, Status

`Status` here refers only to the population estimate for that LGU-year
(official / interpolated / extrapolated) — dengue case counts are official FOI
figures for every year and are not separately flagged.
"""

import pandas as pd

from src.lgu_names import normalize_lgu_name
from src.population import ALL_YEARS


def melt_cases(cases_wide: pd.DataFrame) -> pd.DataFrame:
    """Reshape the wide FOI case-count table into long LGU-Year format."""
    df = cases_wide.copy()
    df["LGU"] = df["LGU"].map(normalize_lgu_name)

    year_columns = [str(y) for y in ALL_YEARS]
    long = df.melt(
        id_vars="LGU",
        value_vars=year_columns,
        var_name="Year",
        value_name="Dengue Cases",
    )
    long["Year"] = long["Year"].astype(int)
    long["Dengue Cases"] = pd.to_numeric(long["Dengue Cases"], errors="raise").astype(int)
    return long


def build_lgu_year_panel(cases_wide: pd.DataFrame, population_panel: pd.DataFrame) -> pd.DataFrame:
    """Merge case counts with the population/density panel into the final 85-row panel.

    Uses an outer-validated one-to-one merge on (LGU, Year) so that a silent
    row drop or duplication during the join fails loudly rather than shrinking
    or inflating the panel unnoticed.
    """
    cases_long = melt_cases(cases_wide)

    merged = cases_long.merge(
        population_panel,
        on=["LGU", "Year"],
        how="inner",
        validate="one_to_one",
    )

    if len(merged) != len(cases_long):
        missing = set(zip(cases_long["LGU"], cases_long["Year"])) - set(
            zip(merged["LGU"], merged["Year"])
        )
        raise ValueError(
            f"Merge dropped {len(cases_long) - len(merged)} LGU-year rows: {sorted(missing)}"
        )

    merged["Incidence Rate"] = merged["Dengue Cases"] / merged["Population"] * 100_000

    ordered = merged[
        [
            "LGU",
            "Year",
            "Dengue Cases",
            "Population",
            "Land Area",
            "Population Density",
            "Incidence Rate",
            "Status",
        ]
    ].sort_values(["LGU", "Year"]).reset_index(drop=True)

    return ordered