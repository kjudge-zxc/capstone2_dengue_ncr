"""NCR-level age and sex descriptive summary.

The FOI release reports age and sex breakdowns for the National Capital Region
as a whole, one table per year, with no LGU disaggregation. They are therefore
kept out of the regression entirely: the unit of analysis everywhere else in the
panel is the LGU-year, and a regional figure cannot serve as an LGU-level
predictor. They are summarised here for the descriptive section of the paper and
the descriptive panel of the dashboard.

Two summaries are produced:

    age summary   one row per year and age band, with that band's share of the year
    sex summary   one row per year, with female and male counts and shares

Both are reconciled against the LGU-level grand totals before being returned, so
the descriptive figures and the modelled figures come from the same numbers.
"""

import pandas as pd

from src.validation import AGE_GROUPS, FOI_GRAND_TOTALS, YEARS

GRAND_TOTAL_LABEL = "Grand Total"


def load_age_sex_tables(raw_dir, years=None) -> dict:
    """Read the per-year age-sex CSVs into a dict keyed by year."""
    years = years or YEARS
    return {
        year: pd.read_csv(f"{raw_dir}/dengue_datasets__age_sex_{year}.csv", thousands=",")
        for year in years
    }


def _body(table: pd.DataFrame) -> pd.DataFrame:
    """Drop the Grand Total row, leaving the thirteen age bands."""
    label_column = table.columns[0]
    body = table[table[label_column].astype(str).str.strip() != GRAND_TOTAL_LABEL].copy()
    body[label_column] = body[label_column].astype(str).str.strip()
    return body.rename(columns={label_column: "Age Group"})


def build_age_summary(tables: dict) -> pd.DataFrame:
    """Long-format age profile: Year, Age Group, Female, Male, Total, Share of Year %."""
    frames = []
    for year, table in sorted(tables.items()):
        body = _body(table)

        if body["Age Group"].tolist() != AGE_GROUPS:
            raise ValueError(f"{year}: age bands are missing or out of order")

        year_total = int(body["Grand Total"].sum())
        if year_total != FOI_GRAND_TOTALS[year]:
            raise ValueError(
                f"{year}: age table sums to {year_total}, FOI grand total is {FOI_GRAND_TOTALS[year]}"
            )

        frame = body[["Age Group", "Female", "Male", "Grand Total"]].copy()
        frame = frame.rename(columns={"Grand Total": "Total"})
        frame.insert(0, "Year", year)
        frame["Share of Year %"] = frame["Total"] / year_total * 100
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def build_sex_summary(tables: dict) -> pd.DataFrame:
    """One row per year: female and male counts, shares, and the male-to-female ratio."""
    rows = []
    for year, table in sorted(tables.items()):
        body = _body(table)
        female, male = int(body["Female"].sum()), int(body["Male"].sum())
        total = female + male

        if total != FOI_GRAND_TOTALS[year]:
            raise ValueError(
                f"{year}: female plus male is {total}, FOI grand total is {FOI_GRAND_TOTALS[year]}"
            )

        rows.append(
            {
                "Year": year,
                "Female": female,
                "Male": male,
                "Total": total,
                "Female %": female / total * 100,
                "Male %": male / total * 100,
                "Male per Female": male / female,
            }
        )
    return pd.DataFrame(rows)


def build_pooled_age_profile(age_summary: pd.DataFrame) -> pd.DataFrame:
    """Age bands pooled across all five years, ordered youngest to oldest."""
    pooled = (
        age_summary.groupby("Age Group", as_index=False)[["Female", "Male", "Total"]]
        .sum()
        .set_index("Age Group")
        .loc[AGE_GROUPS]
        .reset_index()
    )
    pooled["Share of All Years %"] = pooled["Total"] / pooled["Total"].sum() * 100
    return pooled


def summarise_child_share(age_summary: pd.DataFrame, bands=("0-4", "5-9", "10-14")) -> pd.DataFrame:
    """Share of cases in the given age bands, per year.

    The default bands cover ages 0 to 14, the school-age concentration that the
    descriptive section reports.
    """
    selected = age_summary[age_summary["Age Group"].isin(bands)]
    grouped = selected.groupby("Year", as_index=False)["Total"].sum()
    totals = age_summary.groupby("Year", as_index=False)["Total"].sum()
    merged = grouped.merge(totals, on="Year", suffixes=(" in Bands", " All Ages"))
    merged["Share %"] = merged["Total in Bands"] / merged["Total All Ages"] * 100
    return merged
