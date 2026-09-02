"""Descriptive indicators computed from the validated 85-row LGU-year panel.

All four indicators are built on the annual incidence rate, and every
comparison is made within a single LGU across years, never across LGUs:

    incidence rate         cases / population * 100,000, for one LGU-year
    year-over-year change  percent change against the same LGU's previous year
    five-year average      mean incidence across 2021-2025 for that LGU
    current vs average     2025 incidence against that LGU's own five-year average

Comparing an LGU only against itself is what allows a small LGU and a large one
to be read on the same scale. The current-vs-average result is the second of the
two conditions used later in the three-tier priority rule.

Incidence is a descriptive indicator only. The regression is fitted on raw case
counts with a log-population offset, not on the rate.
"""

import numpy as np
import pandas as pd

# Cases are expressed per 100,000 people, the standard denominator used in
# DOH surveillance reporting.
PER_POPULATION = 100_000

CURRENT_YEAR = 2025
PANEL_YEARS = [2021, 2022, 2023, 2024, 2025]


def compute_incidence_rate(cases, population, per=PER_POPULATION):
    """Dengue cases per 100,000 population.

    Accepts either single numbers or pandas Series. Population must be strictly
    positive and cases must be non-negative, so a zero or missing denominator
    fails loudly instead of producing an infinite rate.
    """
    cases_values = np.asarray(cases, dtype=float)
    population_values = np.asarray(population, dtype=float)

    if np.any(~np.isfinite(population_values)) or np.any(population_values <= 0):
        raise ValueError("Population must be a positive number to compute an incidence rate")
    if np.any(~np.isfinite(cases_values)) or np.any(cases_values < 0):
        raise ValueError("Dengue cases must be a non-negative number")

    rate = cases_values / population_values * per

    # Preserve the pandas index when either input came in as a Series, so the
    # result can be assigned straight back onto the panel.
    if isinstance(cases, pd.Series):
        return pd.Series(rate, index=cases.index, name="Incidence Rate")
    if isinstance(population, pd.Series):
        return pd.Series(rate, index=population.index, name="Incidence Rate")
    return float(rate)


def add_incidence_rate(panel: pd.DataFrame) -> pd.DataFrame:
    """Return the panel with an ``Incidence Rate`` column attached."""
    out = panel.copy()
    out["Incidence Rate"] = compute_incidence_rate(out["Dengue Cases"], out["Population"])
    return out


def compute_yoy_change(panel: pd.DataFrame) -> pd.DataFrame:
    """Add ``YoY % Change`` in incidence against the same LGU's previous year.

    The panel is sorted by LGU then year before shifting, so the previous value
    is always the same LGU's own earlier year and never the last row of the LGU
    above it. The first year of each LGU (2021) has no prior year and is left
    empty rather than filled with a zero.
    """
    _require_columns(panel, ["LGU", "Year", "Incidence Rate"])

    out = panel.sort_values(["LGU", "Year"]).reset_index(drop=True)
    previous = out.groupby("LGU")["Incidence Rate"].shift(1)

    if (previous.dropna() <= 0).any():
        raise ValueError("Cannot compute a percent change against a zero prior-year incidence")

    out["Previous Year Incidence"] = previous
    out["YoY % Change"] = (out["Incidence Rate"] - previous) / previous * 100
    return out


def compute_five_year_average(panel: pd.DataFrame) -> pd.DataFrame:
    """Add ``Five-Year Average Incidence``: each LGU's own 2021-2025 mean.

    The value is broadcast to all five rows of that LGU so every row can be read
    against its own benchmark without a second join.
    """
    _require_columns(panel, ["LGU", "Year", "Incidence Rate"])

    counts = panel.groupby("LGU")["Year"].nunique()
    incomplete = counts[counts != len(PANEL_YEARS)]
    if not incomplete.empty:
        raise ValueError(
            "A five-year average needs all five years per LGU; incomplete: "
            f"{incomplete.index.tolist()}"
        )

    out = panel.copy()
    out["Five-Year Average Incidence"] = out.groupby("LGU")["Incidence Rate"].transform("mean")
    return out


def compute_current_vs_average(panel: pd.DataFrame, current_year: int = CURRENT_YEAR) -> pd.DataFrame:
    """One row per LGU comparing current-year incidence with its five-year average.

    Returns LGU, the current-year incidence, the five-year average, the absolute
    difference, the ratio, and ``At or Above Average`` — the boolean condition
    used later as the second half of the three-tier priority rule.
    """
    _require_columns(panel, ["LGU", "Year", "Incidence Rate", "Five-Year Average Incidence"])

    current = panel[panel["Year"] == current_year]
    if current.empty:
        raise ValueError(f"No rows found for year {current_year}")

    out = current[["LGU", "Incidence Rate", "Five-Year Average Incidence"]].copy()
    out = out.rename(columns={"Incidence Rate": f"{current_year} Incidence"})
    out["Difference vs Average"] = out[f"{current_year} Incidence"] - out["Five-Year Average Incidence"]
    out["Ratio vs Average"] = out[f"{current_year} Incidence"] / out["Five-Year Average Incidence"]
    out["At or Above Average"] = out[f"{current_year} Incidence"] >= out["Five-Year Average Incidence"]

    return out.sort_values("LGU").reset_index(drop=True)


def build_indicator_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Run the full indicator chain over the validated panel.

    Adds the incidence rate if it is not already present, then the year-over-year
    change and the five-year average, returning the 85-row panel ready for the
    dashboard export.
    """
    out = panel if "Incidence Rate" in panel.columns else add_incidence_rate(panel)
    out = compute_yoy_change(out)
    out = compute_five_year_average(out)
    return out


def _require_columns(df: pd.DataFrame, columns: list) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Panel is missing required column(s): {missing}")
