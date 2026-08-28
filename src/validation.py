"""Data quality checks for the FOI dengue and PSA census inputs."""

import pandas as pd

NCR_LGUS = [
    "Caloocan", "Las Piñas", "Makati", "Malabon", "Mandaluyong",
    "Manila", "Marikina", "Muntinlupa", "Navotas", "Parañaque",
    "Pasay City", "Pasig", "Pateros", "Quezon City", "San Juan",
    "Taguig", "Valenzuela",
]

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


def check_panel_shape(cases_wide: pd.DataFrame) -> dict:
    """Exactly 17 NCR LGUs, no extras, no omissions."""
    found = set(cases_wide["LGU"].str.strip())
    return {
        "row_count": len(cases_wide),
        "expected_rows": 17,
        "unexpected_lgus": sorted(found - set(NCR_LGUS)),
        "missing_lgus": sorted(set(NCR_LGUS) - found),
        "long_format_rows": len(cases_wide) * len(YEARS),
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