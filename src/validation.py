"""Data quality checks for the FOI dengue and PSA census inputs."""

import pandas as pd
from src.lgu_names import CANONICAL_LGUS, normalize_lgu_name

YEARS = [2021, 2022, 2023, 2024, 2025]

# Grand totals as printed in the FOI release (Table 1)
FOI_GRAND_TOTALS = {2021: 10493, 2022: 43753, 2023: 23678, 2024: 37225, 2025: 45014}

AGE_GROUPS = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34",
    "35-39", "40-44", "45-49", "50-54", "55-60", ">60",
]


def check_grand_totals(cases_wide: pd.DataFrame) -> dict:
    """Sum of LGU case counts must equal the FOI NCR grand total, per year."""
    results = {}
    for year in YEARS:
        computed = int(cases_wide[str(year)].sum())
        reported = FOI_GRAND_TOTALS[year]
        results[year] = {
            "computed": computed,
            "reported": reported,
            "match": computed == reported,
        }
    return results


def check_panel_shape(cases: pd.DataFrame, lgu_column: str = "LGU") -> dict:
    """Exactly 17 NCR LGUs, no extras, no omissions.

    Names are normalised before comparison, so this works on raw source files
    and on the cleaned panel alike.
    """
    raw_names = cases[lgu_column].astype(str).str.strip()

    normalized, unrecognized = [], []
    for name in raw_names:
        try:
            normalized.append(normalize_lgu_name(name))
        except ValueError:
            unrecognized.append(name)

    found = set(normalized)
    return {
        "row_count": len(cases),
        "expected_rows": 17,
        "unrecognized_names": sorted(unrecognized),
        "missing_lgus": sorted(set(CANONICAL_LGUS) - found),
        "duplicate_lgus": sorted({n for n in normalized if normalized.count(n) > 1}),
        "long_format_rows": len(cases) * len(YEARS),
    }

def check_sanity(cases_wide: pd.DataFrame) -> dict:
    """Case counts must be non-negative, non-null integers."""
    counts = cases_wide[[str(y) for y in YEARS]]
    return {
        "negative_values": int((counts < 0).sum().sum()),
        "null_values": int(counts.isna().sum().sum()),
        "min": int(counts.min().min()),
        "max": int(counts.max().max()),
    }


def check_age_sex(age_sex: pd.DataFrame, year: int) -> dict:
    """Age-sex table must have all 13 groups and reconcile to the FOI total."""
    label_col = age_sex.columns[0]
    body = age_sex[age_sex[label_col].astype(str).str.strip() != "Grand Total"]
    labels = body[label_col].astype(str).str.strip().tolist()
    female, male = int(body["Female"].sum()), int(body["Male"].sum())
    total = int(body["Grand Total"].sum())
    return {
        "age_groups_complete": labels == AGE_GROUPS,
        "female": female,
        "male": male,
        "total": total,
        "sums_to_total": female + male == total,
        "matches_foi": total == FOI_GRAND_TOTALS[year],
    }


def check_census_totals(pop_2020: pd.DataFrame, pop_2024: pd.DataFrame) -> dict:
    """Census files must match published PSA regional totals."""
    return {
        2020: {
            "computed": int(pop_2020["Total Population"].sum()),
            "reported": 13_484_462,
            "match": int(pop_2020["Total Population"].sum()) == 13_484_462,
        },
        2024: {
            "computed": int(pop_2024["Total Population"].sum()),
            "reported": 14_001_751,
            "match": int(pop_2024["Total Population"].sum()) == 14_001_751,
        },
    }



# ---------------------------------------------------------------------------
# Structural and range validation
# ---------------------------------------------------------------------------

# Plausibility bounds. These are set from the
# observed range of the source data with generous headroom. They are intended to
# catch data entry and unit errors, not to reject legitimate variation.
#
#   population   observed 65,227 - 3,084,270   (Pateros to Quezon City)
#   land_area    observed 5.95 - 171.71 km2    (San Juan to Quezon City)
#   density      observed ~6,400 - ~76,000     (Pateros to Manila)
#   incidence    observed 35.9 - 733.8         per 100,000

RANGES = {
    "population": (10_000, 5_000_000),
    "land_area": (1.0, 500.0),
    "density": (100.0, 200_000.0),
    "incidence": (0.0, 2_000.0),
}


def check_duplicates(df: pd.DataFrame, keys: list) -> dict:
    """No repeated records for the given key columns.

    On the raw wide file the key is LGU alone; on the long panel it is
    LGU and year together.
    """
    dupes = df[df.duplicated(subset=keys, keep=False)]
    return {
        "keys": keys,
        "duplicate_row_count": len(dupes),
        "duplicate_keys": dupes[keys].drop_duplicates().values.tolist(),
    }


def check_missing(df: pd.DataFrame, required_columns: list) -> dict:
    """Required columns are present and contain no nulls or blanks."""
    absent = [c for c in required_columns if c not in df.columns]
    present = [c for c in required_columns if c in df.columns]

    nulls = {c: int(df[c].isna().sum()) for c in present if df[c].isna().any()}
    blanks = {
        c: int((df[c].astype(str).str.strip() == "").sum())
        for c in present
        if df[c].dtype == object and (df[c].astype(str).str.strip() == "").any()
    }
    return {
        "absent_columns": absent,
        "columns_with_nulls": nulls,
        "columns_with_blanks": blanks,
    }


def check_dtypes(df: pd.DataFrame, expected: dict) -> dict:
    """Columns hold the expected kind of value.

    ``expected`` maps column name to "integer", "numeric" or "text". Values are
    tested by coercion rather than by dtype, since a CSV read can leave a numeric
    column as object if a single cell contains a stray character.
    """
    results = {}
    for column, kind in expected.items():
        if column not in df.columns:
            results[column] = {"ok": False, "reason": "column absent"}
            continue

        series = df[column]
        if kind == "text":
            ok = series.map(lambda v: isinstance(v, str)).all()
            results[column] = {"ok": bool(ok), "reason": "" if ok else "non-text values"}
            continue

        coerced = pd.to_numeric(series, errors="coerce")
        bad = int(coerced.isna().sum() - series.isna().sum())
        if bad:
            results[column] = {"ok": False, "reason": f"{bad} non-numeric values"}
        elif kind == "integer" and not (coerced.dropna() % 1 == 0).all():
            results[column] = {"ok": False, "reason": "non-integer values"}
        else:
            results[column] = {"ok": True, "reason": ""}
    return results


def check_ranges(df: pd.DataFrame, column_kinds: dict, ranges: dict = None) -> dict:
    """Numeric columns fall within plausible bounds.

    ``column_kinds`` maps a column name to a key in ``RANGES``, e.g.
    ``{"Total Population": "population", "Land Area": "land_area"}``.
    """
    ranges = ranges or RANGES
    results = {}
    for column, kind in column_kinds.items():
        if column not in df.columns:
            results[column] = {"ok": False, "reason": "column absent"}
            continue

        low, high = ranges[kind]
        values = pd.to_numeric(df[column], errors="coerce")
        below = values[values < low]
        above = values[values > high]
        results[column] = {
            "ok": below.empty and above.empty,
            "bounds": (low, high),
            "observed_min": None if values.dropna().empty else float(values.min()),
            "observed_max": None if values.dropna().empty else float(values.max()),
            "below_bound": int(len(below)),
            "above_bound": int(len(above)),
        }
    return results


def check_cases_within_regional_total(cases: pd.DataFrame) -> dict:
    """No single LGU may report more cases than the NCR total for that year.

    A logical ceiling derived from the data rather than an arbitrary threshold.
    """
    results = {}
    for year in YEARS:
        ceiling = FOI_GRAND_TOTALS[year]
        column = pd.to_numeric(cases[str(year)], errors="coerce")
        offenders = cases.loc[column > ceiling, cases.columns[0]].tolist()
        results[year] = {
            "ceiling": ceiling,
            "max_observed": int(column.max()),
            "exceeding_lgus": offenders,
            "ok": not offenders,
        }
    return results