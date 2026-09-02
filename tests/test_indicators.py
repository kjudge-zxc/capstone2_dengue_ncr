import pandas as pd
import pytest
from pathlib import Path

from src.indicators import (
    PER_POPULATION,
    compute_incidence_rate,
    add_incidence_rate,
    compute_yoy_change,
    compute_five_year_average,
    compute_current_vs_average,
    build_indicator_panel,
)

VALIDATED = Path(__file__).parent.parent / "data" / "04_validated"


@pytest.fixture
def panel():
    return pd.read_csv(VALIDATED / "lgu_year_panel.csv")


@pytest.fixture
def indicators(panel):
    return build_indicator_panel(panel)


# --- incidence rate: the formula itself ------------------------------------

def test_incidence_rate_basic_case():
    # 100 cases in a population of 200,000 is 50 per 100,000
    assert compute_incidence_rate(100, 200_000) == pytest.approx(50.0)


def test_incidence_rate_uses_a_100k_denominator():
    assert PER_POPULATION == 100_000
    assert compute_incidence_rate(1, 100_000) == pytest.approx(1.0)


def test_zero_cases_gives_zero_incidence():
    assert compute_incidence_rate(0, 500_000) == 0.0


def test_incidence_is_unchanged_when_cases_and_population_scale_together():
    # A rate must not depend on the size of the LGU
    assert compute_incidence_rate(50, 100_000) == pytest.approx(
        compute_incidence_rate(500, 1_000_000)
    )


def test_incidence_rejects_zero_or_negative_population():
    for bad in (0, -1, -250_000):
        with pytest.raises(ValueError):
            compute_incidence_rate(100, bad)


def test_incidence_rejects_negative_cases():
    with pytest.raises(ValueError):
        compute_incidence_rate(-5, 100_000)


def test_incidence_rejects_missing_values():
    with pytest.raises(ValueError):
        compute_incidence_rate(100, float("nan"))


def test_incidence_accepts_series_and_preserves_the_index():
    cases = pd.Series([100, 200], index=[7, 9])
    population = pd.Series([100_000, 100_000], index=[7, 9])
    result = compute_incidence_rate(cases, population)
    assert result.index.tolist() == [7, 9]
    assert result.tolist() == pytest.approx([100.0, 200.0])


def test_series_result_matches_elementwise_computation():
    cases = pd.Series([1051, 4371, 77])
    population = pd.Series([1_674_424.25, 1_687_264.5, 65_749.0])
    vectorised = compute_incidence_rate(cases, population)
    for i in range(3):
        assert vectorised.iloc[i] == pytest.approx(
            compute_incidence_rate(cases.iloc[i], population.iloc[i])
        )


# --- incidence rate against the real panel ---------------------------------

def test_panel_incidence_matches_the_function_for_all_85_rows(panel):
    recomputed = compute_incidence_rate(panel["Dengue Cases"], panel["Population"])
    assert (panel["Incidence Rate"] - recomputed).abs().max() < 1e-9


def test_add_incidence_rate_reproduces_the_stored_column(panel):
    stripped = panel.drop(columns=["Incidence Rate"])
    rebuilt = add_incidence_rate(stripped)
    assert (rebuilt["Incidence Rate"] - panel["Incidence Rate"]).abs().max() < 1e-9


def test_known_row_quezon_city_2025(panel):
    row = panel[(panel["LGU"] == "Quezon City") & (panel["Year"] == 2025)].iloc[0]
    assert row["Incidence Rate"] == pytest.approx(
        11071 / row["Population"] * 100_000
    )


# --- year-over-year change --------------------------------------------------

def test_yoy_change_on_a_known_doubling():
    frame = pd.DataFrame(
        {"LGU": ["A", "A"], "Year": [2021, 2022], "Incidence Rate": [100.0, 150.0]}
    )
    result = compute_yoy_change(frame)
    assert result.loc[1, "YoY % Change"] == pytest.approx(50.0)


def test_yoy_change_is_negative_for_a_decline():
    frame = pd.DataFrame(
        {"LGU": ["A", "A"], "Year": [2021, 2022], "Incidence Rate": [200.0, 150.0]}
    )
    assert compute_yoy_change(frame).loc[1, "YoY % Change"] == pytest.approx(-25.0)


def test_first_year_has_no_yoy_value(indicators):
    first_year = indicators[indicators["Year"] == 2021]
    assert first_year["YoY % Change"].isna().all()
    assert indicators[indicators["Year"] > 2021]["YoY % Change"].notna().all()


def test_yoy_never_compares_across_lgus():
    # Two LGUs sitting next to each other in the file: B's 2022 value must be
    # measured against B's own 2021 value, not against A's last row.
    frame = pd.DataFrame(
        {
            "LGU": ["A", "A", "B", "B"],
            "Year": [2021, 2022, 2021, 2022],
            "Incidence Rate": [100.0, 400.0, 50.0, 75.0],
        }
    )
    result = compute_yoy_change(frame)
    b_2022 = result[(result["LGU"] == "B") & (result["Year"] == 2022)].iloc[0]
    assert b_2022["YoY % Change"] == pytest.approx(50.0)
    assert result[result["Year"] == 2021]["YoY % Change"].isna().all()


def test_yoy_uses_the_prior_year_even_if_rows_arrive_out_of_order():
    shuffled = pd.DataFrame(
        {
            "LGU": ["A", "A", "A"],
            "Year": [2023, 2021, 2022],
            "Incidence Rate": [300.0, 100.0, 200.0],
        }
    )
    result = compute_yoy_change(shuffled)
    by_year = result.set_index("Year")["YoY % Change"]
    assert by_year[2022] == pytest.approx(100.0)
    assert by_year[2023] == pytest.approx(50.0)


def test_yoy_requires_an_incidence_column():
    with pytest.raises(ValueError):
        compute_yoy_change(pd.DataFrame({"LGU": ["A"], "Year": [2021]}))


# --- five-year average ------------------------------------------------------

def test_five_year_average_is_the_mean_of_the_five_values():
    frame = pd.DataFrame(
        {
            "LGU": ["A"] * 5,
            "Year": [2021, 2022, 2023, 2024, 2025],
            "Incidence Rate": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )
    result = compute_five_year_average(frame)
    assert result["Five-Year Average Incidence"].unique().tolist() == [300.0]


def test_five_year_average_is_computed_per_lgu(indicators):
    for lgu, group in indicators.groupby("LGU"):
        assert group["Five-Year Average Incidence"].nunique() == 1
        assert group["Five-Year Average Incidence"].iloc[0] == pytest.approx(
            group["Incidence Rate"].mean()
        )


def test_five_year_average_rejects_an_incomplete_lgu(indicators):
    truncated = indicators[
        ~((indicators["LGU"] == "Pateros") & (indicators["Year"] == 2023))
    ]
    with pytest.raises(ValueError):
        compute_five_year_average(truncated)


# --- current year against the five-year average -----------------------------

def test_current_vs_average_returns_one_row_per_lgu(indicators):
    comparison = compute_current_vs_average(indicators)
    assert len(comparison) == 17
    assert comparison["LGU"].nunique() == 17


def test_at_or_above_average_is_true_on_an_exact_tie():
    frame = pd.DataFrame(
        {
            "LGU": ["A"] * 5,
            "Year": [2021, 2022, 2023, 2024, 2025],
            "Incidence Rate": [100.0, 100.0, 100.0, 100.0, 100.0],
        }
    )
    comparison = compute_current_vs_average(compute_five_year_average(frame))
    assert bool(comparison.loc[0, "At or Above Average"]) is True
    assert comparison.loc[0, "Difference vs Average"] == pytest.approx(0.0)
    assert comparison.loc[0, "Ratio vs Average"] == pytest.approx(1.0)


def test_below_average_lgu_is_flagged_false():
    frame = pd.DataFrame(
        {
            "LGU": ["A"] * 5,
            "Year": [2021, 2022, 2023, 2024, 2025],
            "Incidence Rate": [500.0, 500.0, 500.0, 500.0, 100.0],
        }
    )
    comparison = compute_current_vs_average(compute_five_year_average(frame))
    assert bool(comparison.loc[0, "At or Above Average"]) is False
    assert comparison.loc[0, "Difference vs Average"] < 0


def test_current_vs_average_rejects_a_year_not_in_the_panel(indicators):
    with pytest.raises(ValueError):
        compute_current_vs_average(indicators, current_year=2030)


# --- the assembled indicator panel -----------------------------------------

def test_indicator_panel_keeps_all_85_rows(indicators):
    assert len(indicators) == 85
    assert indicators["LGU"].nunique() == 17


def test_indicator_panel_adds_the_expected_columns(indicators):
    for column in ["Incidence Rate", "YoY % Change", "Five-Year Average Incidence"]:
        assert column in indicators.columns


def test_indicator_panel_leaves_source_columns_untouched(panel, indicators):
    merged = panel.merge(indicators, on=["LGU", "Year"], suffixes=("_before", "_after"))
    assert (merged["Dengue Cases_before"] == merged["Dengue Cases_after"]).all()
    assert (merged["Population_before"] - merged["Population_after"]).abs().max() < 1e-9
