import pandas as pd
import pytest
from pathlib import Path

from src.validation import (
    YEARS, FOI_GRAND_TOTALS,
    check_grand_totals, check_panel_shape, check_sanity,
    check_age_sex, check_census_totals,
)

RAW = Path(__file__).parent.parent / "data" / "01_raw"
REF = Path(__file__).parent.parent / "data" / "02_official_reference"


@pytest.fixture
def cases():
    return pd.read_csv(RAW / "dengue_datasets__local_govt_level.csv", thousands=",")


def test_grand_totals_match_foi(cases):
    for year, r in check_grand_totals(cases).items():
        assert r["match"], f"{year}: computed {r['computed']} != FOI {r['reported']}"


def test_seventeen_lgus_no_surprises(cases):
    r = check_panel_shape(cases)
    assert r["row_count"] == 17
    assert r["unexpected_lgus"] == []
    assert r["missing_lgus"] == []
    assert r["long_format_rows"] == 85


def test_counts_are_plausible(cases):
    r = check_sanity(cases)
    assert r["negative_values"] == 0
    assert r["null_values"] == 0


@pytest.mark.parametrize("year", YEARS)
def test_age_sex_reconciles(year):
    df = pd.read_csv(RAW / f"dengue_datasets__age_sex_{year}.csv")
    r = check_age_sex(df, year)
    assert r["age_groups_complete"]
    assert r["sums_to_total"]
    assert r["matches_foi"], f"{year}: {r['total']} != {FOI_GRAND_TOTALS[year]}"


def test_census_totals_match_psa():
    p20 = pd.read_csv(REF / "ncr_population_masterlist__2020.csv")
    p24 = pd.read_csv(REF / "ncr_population_masterlist__2024.csv")
    for year, r in check_census_totals(p20, p24).items():
        assert r["match"], f"{year}: {r['computed']} != {r['reported']}"