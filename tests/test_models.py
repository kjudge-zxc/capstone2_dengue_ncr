import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.models import (
    DENSITY_SCALE,
    build_design_matrix,
    fit_poisson_baseline,
    fit_quasi_poisson,
    overdispersion_index,
    deviance_ratio,
    overdispersion_report,
    coefficient_table,
)

VALIDATED = Path(__file__).parent.parent / "data" / "04_validated"


@pytest.fixture
def panel():
    return pd.read_csv(VALIDATED / "lgu_year_panel.csv")


@pytest.fixture
def fitted(panel):
    return fit_poisson_baseline(panel)


def synthetic_panel(rng, dispersion=None, n_lgus=17, years=(2021, 2022, 2023, 2024, 2025)):
    """Build a panel with a known data-generating process.

    ``dispersion=None`` draws pure Poisson counts, so a correctly specified
    model should report an overdispersion index near 1. A numeric value draws
    Negative Binomial counts with that much extra variance.
    """
    rows = []
    for i in range(n_lgus):
        population = rng.uniform(100_000, 3_000_000)
        land_area = rng.uniform(10, 150)
        density = population / land_area
        for year in years:
            rate = np.exp(-7 + 0.004 * (density / DENSITY_SCALE))
            mean = rate * population
            if dispersion is None:
                cases = rng.poisson(mean)
            else:
                p = 1 / (1 + dispersion * mean)
                cases = rng.negative_binomial(1 / dispersion, p)
            rows.append(
                {
                    "LGU": f"LGU{i:02d}",
                    "Year": year,
                    "Dengue Cases": int(cases),
                    "Population": population,
                    "Population Density": density,
                }
            )
    return pd.DataFrame(rows)


# --- design matrix ----------------------------------------------------------

def test_design_matrix_has_intercept_density_and_four_year_dummies(panel):
    design = build_design_matrix(panel)
    assert "const" in design.columns
    assert "Density per 1000" in design.columns
    # 2021 is the reference year, so 2022-2025 get dummies
    assert [c for c in design.columns if c.startswith("Year_")] == [
        "Year_2022", "Year_2023", "Year_2024", "Year_2025"
    ]


def test_density_is_scaled_to_thousands(panel):
    design = build_design_matrix(panel)
    assert design["Density per 1000"].iloc[0] == pytest.approx(
        panel["Population Density"].iloc[0] / 1000
    )


def test_numeric_year_option_gives_a_single_year_term(panel):
    design = build_design_matrix(panel, year_as="numeric")
    assert "Year Index" in design.columns
    assert not [c for c in design.columns if c.startswith("Year_2")]
    assert design["Year Index"].min() == 0
    assert design["Year Index"].max() == 4


def test_unknown_year_option_is_rejected(panel):
    with pytest.raises(ValueError):
        build_design_matrix(panel, year_as="quarterly")


# --- the offset -------------------------------------------------------------

def test_offset_is_log_population(panel, fitted):
    assert fitted.model.offset == pytest.approx(np.log(panel["Population"]).values)


@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.PerfectSeparationWarning")
def test_offset_makes_the_model_estimate_rates_not_counts():
    # Two LGUs with the same incidence rate but very different sizes and
    # densities. With population as an offset the model must not read the
    # larger, denser one as higher risk: the density coefficient stays at zero
    # and the intercept recovers the shared underlying rate.
    rows = []
    for i, (population, density) in enumerate([(100_000, 10_000), (2_000_000, 40_000)]):
        for year in range(2021, 2026):
            rows.append(
                {
                    "LGU": f"LGU{i}",
                    "Year": year,
                    "Population": population,
                    "Population Density": density,
                    "Dengue Cases": int(population * 0.002),
                }
            )
    result = fit_poisson_baseline(pd.DataFrame(rows), year_as="none")
    assert result.params["Density per 1000"] == pytest.approx(0.0, abs=1e-6)
    # exp(intercept) recovers the common underlying rate of 0.002
    assert np.exp(result.params["const"]) == pytest.approx(0.002, rel=0.01)


# --- fitting on the real panel ---------------------------------------------

def test_model_uses_all_85_observations(fitted):
    assert fitted.nobs == 85


def test_residual_degrees_of_freedom_is_observations_minus_parameters(fitted):
    # 85 rows, 6 estimated parameters: intercept, density, four year dummies
    assert int(fitted.df_resid) == 85 - 6


def test_fit_converges(fitted):
    assert fitted.converged
    assert np.isfinite(fitted.llf)


def test_fitted_values_are_positive_and_of_the_right_length(fitted):
    assert len(fitted.fittedvalues) == 85
    assert (fitted.fittedvalues > 0).all()


def test_coefficient_table_rate_ratios_are_exponentiated_coefficients(fitted):
    table = coefficient_table(fitted)
    assert table.loc["Density per 1000", "Rate Ratio"] == pytest.approx(
        np.exp(fitted.params["Density per 1000"])
    )


# --- input validation -------------------------------------------------------

def test_fit_rejects_a_panel_missing_a_required_column(panel):
    with pytest.raises(ValueError):
        fit_poisson_baseline(panel.drop(columns=["Population Density"]))


def test_fit_rejects_non_positive_population(panel):
    tampered = panel.copy()
    tampered.loc[0, "Population"] = 0
    with pytest.raises(ValueError):
        fit_poisson_baseline(tampered)


def test_fit_rejects_negative_case_counts(panel):
    tampered = panel.copy()
    tampered.loc[0, "Dengue Cases"] = -1
    with pytest.raises(ValueError):
        fit_poisson_baseline(tampered)


# --- overdispersion index ---------------------------------------------------

def test_index_equals_pearson_chi2_over_residual_df(fitted):
    assert overdispersion_index(fitted) == pytest.approx(
        float(fitted.pearson_chi2) / int(fitted.df_resid)
    )


def test_deviance_ratio_equals_deviance_over_residual_df(fitted):
    assert deviance_ratio(fitted) == pytest.approx(
        float(fitted.deviance) / int(fitted.df_resid)
    )


def test_index_is_near_one_for_genuinely_poisson_data():
    # The check must not report overdispersion where there is none
    rng = np.random.default_rng(42)
    result = fit_poisson_baseline(synthetic_panel(rng), year_as="none")
    assert 0.5 < overdispersion_index(result) < 2.0


def test_index_is_large_for_overdispersed_data():
    # The check must detect extra variance when it is present
    rng = np.random.default_rng(42)
    result = fit_poisson_baseline(synthetic_panel(rng, dispersion=0.5), year_as="none")
    assert overdispersion_index(result) > 5


def test_report_carries_both_statistics_and_a_verdict(fitted):
    report = overdispersion_report(fitted)
    assert report["observations"] == 85
    assert report["df_resid"] == 79
    assert report["overdispersion_index"] == pytest.approx(overdispersion_index(fitted))
    assert report["deviance_ratio"] == pytest.approx(deviance_ratio(fitted))
    assert isinstance(report["verdict"], str) and report["verdict"]


def test_verdict_wording_follows_the_index():
    rng = np.random.default_rng(7)
    clean = fit_poisson_baseline(synthetic_panel(rng), year_as="none")
    overdispersed = fit_poisson_baseline(synthetic_panel(rng, dispersion=0.5), year_as="none")
    assert "adequate" in overdispersion_report(clean)["verdict"]
    assert "Negative Binomial" in overdispersion_report(overdispersed)["verdict"]


def test_real_panel_is_overdispersed(fitted):
    # The finding that justifies the study's Negative Binomial specification
    assert overdispersion_index(fitted) > 2


# --- quasi-Poisson diagnostic ----------------------------------------------

def test_quasi_poisson_leaves_coefficients_unchanged(panel, fitted):
    scaled = fit_quasi_poisson(panel)
    assert scaled.params.values == pytest.approx(fitted.params.values)


def test_quasi_poisson_inflates_standard_errors_by_sqrt_of_the_index(panel, fitted):
    scaled = fit_quasi_poisson(panel)
    factor = np.sqrt(overdispersion_index(fitted))
    assert scaled.bse.values == pytest.approx(fitted.bse.values * factor, rel=1e-6)


def test_poisson_standard_errors_are_the_smaller_ones(panel, fitted):
    scaled = fit_quasi_poisson(panel)
    assert (scaled.bse > fitted.bse).all()
