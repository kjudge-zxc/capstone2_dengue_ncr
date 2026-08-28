import pandas as pd
import pytest
from pathlib import Path

from src.validation import (
    RANGES,
    check_duplicates,
    check_missing,
    check_dtypes,
    check_ranges,
    check_cases_within_regional_total,
)

RAW = Path(__file__).parent.parent / "data" / "01_raw"
REF = Path(__file__).parent.parent / "data" / "02_official_reference"


@pytest.fixture
def cases():
    return pd.read_csv(RAW / "dengue_datasets__local_govt_level.csv", thousands=",")


@pytest.fixture(params=["2020", "2024"])
def population(request):
    return pd.read_csv(REF / f"ncr_population_masterlist__{request.param}.csv")


# --- structural checks on the real source files -----------------------------

def test_no_duplicate_lgus(cases):
    assert check_duplicates(cases, ["LGU"])["duplicate_row_count"] == 0


def test_no_missing_values_in_cases(cases):
    r = check_missing(cases, ["LGU", "2021", "2022", "2023", "2024", "2025"])
    assert r["absent_columns"] == []
    assert r["columns_with_nulls"] == {}
    assert r["columns_with_blanks"] == {}


def test_case_counts_are_integers(cases):
    spec = {"LGU": "text", **{str(y): "integer" for y in range(2021, 2026)}}
    for column, result in check_dtypes(cases, spec).items():
        assert result["ok"], f"{column}: {result['reason']}"


def test_no_lgu_exceeds_regional_total(cases):
    for year, r in check_cases_within_regional_total(cases).items():
        assert r["ok"], f"{year}: {r['exceeding_lgus']} exceed {r['ceiling']}"


def test_population_and_land_area_within_bounds(population):
    kinds = {"Total Population": "population", "Land Area": "land_area"}
    for column, r in check_ranges(population, kinds).items():
        assert r["ok"], (
            f"{column}: observed {r['observed_min']}-{r['observed_max']}, "
            f"bounds {r['bounds']}"
        )


def test_no_duplicate_lgus_in_population(population):
    assert check_duplicates(population, ["City and Municipality"])["duplicate_row_count"] == 0


# --- the checks must actually catch bad data --------------------------------

def test_duplicate_detection_catches_a_repeat(cases):
    injected = pd.concat([cases, cases.iloc[[0]]], ignore_index=True)
    r = check_duplicates(injected, ["LGU"])
    assert r["duplicate_row_count"] == 2
    assert r["duplicate_keys"] == [["Caloocan"]]


def test_null_detection_catches_a_blank(cases):
    injected = cases.copy()
    injected.loc[3, "2023"] = None
    assert check_missing(injected, ["2023"])["columns_with_nulls"] == {"2023": 1}


def test_dtype_detection_catches_stray_text(cases):
    injected = cases.copy()
    injected["2022"] = injected["2022"].astype(object)
    injected.loc[5, "2022"] = "n/a"
    assert not check_dtypes(injected, {"2022": "integer"})["2022"]["ok"]


def test_range_detection_catches_a_dropped_digit(population):
    injected = population.copy()
    injected.loc[0, "Total Population"] = 6_522     # Pateros missing a digit
    r = check_ranges(injected, {"Total Population": "population"})
    assert not r["Total Population"]["ok"]
    assert r["Total Population"]["below_bound"] == 1


def test_range_detection_catches_a_unit_error(population):
    injected = population.copy()
    injected["Land Area"] = injected["Land Area"] * 100    # km2 recorded as hectares
    assert not check_ranges(injected, {"Land Area": "land_area"})["Land Area"]["ok"]


def test_regional_ceiling_catches_an_impossible_count(cases):
    injected = cases.copy()
    injected.loc[0, "2021"] = 99_999
    r = check_cases_within_regional_total(injected)
    assert not r[2021]["ok"]
    assert "Caloocan" in r[2021]["exceeding_lgus"]


def test_bounds_are_documented():
    for kind, (low, high) in RANGES.items():
        assert low < high, f"{kind} bounds are inverted"