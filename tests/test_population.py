import pandas as pd
import pytest
from pathlib import Path

from src.population import (
    ANCHOR_YEAR_0,
    ANCHOR_YEAR_1,
    ALL_YEARS,
    STATUS_OFFICIAL,
    STATUS_INTERPOLATED,
    STATUS_EXTRAPOLATED,
    estimate_population,
    compute_density,
    build_population_panel,
)

REF = Path(__file__).parent.parent / "data" / "02_official_reference"


@pytest.fixture
def pop_2020():
    return pd.read_csv(REF / "ncr_population_masterlist__2020.csv")


@pytest.fixture
def pop_2024():
    return pd.read_csv(REF / "ncr_population_masterlist__2024.csv")


# --- anchor behaviour ---

def test_anchors_are_2020_and_2024():
    assert ANCHOR_YEAR_0 == 2020
    assert ANCHOR_YEAR_1 == 2024


def test_estimate_at_2020_returns_p0_unchanged():
    assert estimate_population(p0=1_000_000, p1=1_200_000, year=2020) == 1_000_000


def test_estimate_at_2024_returns_p1_unchanged():
    assert estimate_population(p0=1_000_000, p1=1_200_000, year=2024) == 1_200_000


def test_interpolated_years_fall_strictly_between_anchors_for_growth():
    p0, p1 = 1_000_000, 1_200_000
    for year in (2021, 2022, 2023):
        est = estimate_population(p0, p1, year)
        assert p0 < est < p1, f"{year}: {est} not between anchors"


def test_interpolation_is_linear_and_evenly_spaced():
    p0, p1 = 1_000_000, 1_200_000
    step = (p1 - p0) / 4  # 4 intervals across 2020-2024
    for i, year in enumerate((2021, 2022, 2023), start=1):
        expected = p0 + step * i
        assert estimate_population(p0, p1, year) == pytest.approx(expected)


def test_extrapolation_continues_the_same_growth_rate_beyond_2024():
    p0, p1 = 1_000_000, 1_200_000
    annual_growth = (p1 - p0) / 4
    expected_2025 = p1 + annual_growth
    assert estimate_population(p0, p1, 2025) == pytest.approx(expected_2025)


def test_extrapolation_uses_same_formula_as_interpolation():
    # The 2025 estimate should sit on the same line as the 2021-2023 estimates.
    p0, p1 = 500_000, 800_000
    ests = {year: estimate_population(p0, p1, year) for year in (2021, 2022, 2023, 2025)}
    diffs = [ests[y] - ests[y - 1] for y in (2022, 2023)]
    step_2024_2025 = ests[2025] - p1
    for d in diffs:
        assert d == pytest.approx(diffs[0])
    assert step_2024_2025 == pytest.approx(diffs[0])


def test_declining_population_extrapolates_downward():
    # A shrinking LGU (e.g. Makati 2020->2024) must extrapolate further down, not snap back upward, for 2025
    p0, p1 = 629_616, 309_770
    est_2025 = estimate_population(p0, p1, 2025)
    assert est_2025 < p1


@pytest.mark.parametrize("year", [2019, 2018])
def test_years_before_the_first_anchor_are_rejected(year):
    with pytest.raises(ValueError):
        estimate_population(1_000_000, 1_200_000, year)


# --- status labelling ---

def test_status_labels_by_year():
    panel = build_population_panel(
        pd.read_csv(REF / "ncr_population_masterlist__2020.csv"),
        pd.read_csv(REF / "ncr_population_masterlist__2024.csv"),
    )
    status_by_year = panel.drop_duplicates("Year").set_index("Year")["Status"].to_dict()
    assert status_by_year[2020] if 2020 in status_by_year else True  # 2020 not in panel scope
    assert status_by_year[2021] == STATUS_INTERPOLATED
    assert status_by_year[2022] == STATUS_INTERPOLATED
    assert status_by_year[2023] == STATUS_INTERPOLATED
    assert status_by_year[2024] == STATUS_OFFICIAL
    assert status_by_year[2025] == STATUS_EXTRAPOLATED


def test_2024_values_match_official_source_exactly(pop_2020, pop_2024):
    panel = build_population_panel(pop_2020, pop_2024)
    y2024 = panel[panel["Year"] == 2024].set_index("LGU")["Population"]
    official = pop_2024.copy()
    from src.lgu_names import normalize_lgu_name
    official["LGU"] = official["City and Municipality"].map(normalize_lgu_name)
    official = official.set_index("LGU")["Total Population"]
    for lgu in official.index:
        assert y2024[lgu] == pytest.approx(official[lgu]), f"{lgu}: 2024 figure was recomputed, not used directly"


# --- density ---

def test_compute_density_basic():
    assert compute_density(population=1000, land_area=10) == 100


def test_compute_density_rejects_nonpositive_land_area():
    with pytest.raises(ValueError):
        compute_density(population=1000, land_area=0)


def test_land_area_is_constant_across_all_years_per_lgu(pop_2020, pop_2024):
    panel = build_population_panel(pop_2020, pop_2024)
    for lgu, group in panel.groupby("LGU"):
        assert group["Land Area"].nunique() == 1, f"{lgu}: land area varies by year"


# --- panel shape and completeness ---

def test_panel_has_exactly_85_rows(pop_2020, pop_2024):
    panel = build_population_panel(pop_2020, pop_2024)
    assert len(panel) == 85


def test_panel_has_17_lgus_and_5_years(pop_2020, pop_2024):
    panel = build_population_panel(pop_2020, pop_2024)
    assert panel["LGU"].nunique() == 17
    assert sorted(panel["Year"].unique().tolist()) == ALL_YEARS


def test_panel_has_no_duplicate_lgu_year_keys(pop_2020, pop_2024):
    panel = build_population_panel(pop_2020, pop_2024)
    assert panel.duplicated(subset=["LGU", "Year"]).sum() == 0


def test_panel_raises_on_land_area_mismatch_between_sources(pop_2020, pop_2024):
    tampered = pop_2024.copy()
    tampered.loc[0, "Land Area"] = tampered.loc[0, "Land Area"] + 5
    with pytest.raises(ValueError):
        build_population_panel(pop_2020, tampered)