import pandas as pd
import pytest
from pathlib import Path

from src.population import build_population_panel
from src.panel import melt_cases, build_lgu_year_panel

RAW = Path(__file__).parent.parent / "data" / "01_raw"
REF = Path(__file__).parent.parent / "data" / "02_official_reference"


@pytest.fixture
def cases_wide():
    return pd.read_csv(RAW / "dengue_datasets__local_govt_level.csv", thousands=",")


@pytest.fixture
def population_panel():
    return build_population_panel(
        pd.read_csv(REF / "ncr_population_masterlist__2020.csv"),
        pd.read_csv(REF / "ncr_population_masterlist__2024.csv"),
    )


@pytest.fixture
def panel(cases_wide, population_panel):
    return build_lgu_year_panel(cases_wide, population_panel)


# --- melt step ---

def test_melt_produces_85_rows(cases_wide):
    assert len(melt_cases(cases_wide)) == 85


def test_melt_preserves_a_known_value(cases_wide):
    long = melt_cases(cases_wide)
    row = long[(long["LGU"] == "Quezon City") & (long["Year"] == 2025)]
    assert row["Dengue Cases"].iloc[0] == 11071


# --- merge step: the required 85-row check ---

def test_merged_panel_returns_exactly_85_rows(panel):
    assert len(panel) == 85


def test_merged_panel_has_17_lgus_and_5_years(panel):
    assert panel["LGU"].nunique() == 17
    assert sorted(panel["Year"].unique().tolist()) == [2021, 2022, 2023, 2024, 2025]


def test_merged_panel_has_no_duplicate_keys(panel):
    assert panel.duplicated(subset=["LGU", "Year"]).sum() == 0


def test_merged_panel_has_no_null_values(panel):
    assert panel.isna().sum().sum() == 0


def test_merge_raises_if_a_lgu_year_is_missing_from_population(cases_wide, population_panel):
    truncated = population_panel[
        ~((population_panel["LGU"] == "Pateros") & (population_panel["Year"] == 2023))
    ]
    with pytest.raises(ValueError):
        build_lgu_year_panel(cases_wide, truncated)


# --- spot-check a known row end to end ---

def test_quezon_city_2025_row_values(panel):
    row = panel[(panel["LGU"] == "Quezon City") & (panel["Year"] == 2025)].iloc[0]
    assert row["Dengue Cases"] == 11071
    assert row["Status"] == "extrapolated"
    assert row["Land Area"] == pytest.approx(171.71)
    # Incidence rate must equal cases / population * 100,000 exactly
    expected_ir = row["Dengue Cases"] / row["Population"] * 100_000
    assert row["Incidence Rate"] == pytest.approx(expected_ir)


def test_incidence_rate_matches_manual_formula_for_every_row(panel):
    recomputed = panel["Dengue Cases"] / panel["Population"] * 100_000
    assert (panel["Incidence Rate"] - recomputed).abs().max() < 1e-9


def test_density_matches_manual_formula_for_every_row(panel):
    recomputed = panel["Population"] / panel["Land Area"]
    assert (panel["Population Density"] - recomputed).abs().max() < 1e-9