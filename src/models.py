"""Poisson baseline model and the overdispersion check that follows from it.

The study's final model is Negative Binomial, but the Poisson fit is estimated
first and kept in the repository as the baseline. It serves one purpose: to
measure how far the count data departs from the equal mean and variance that
Poisson assumes, and so to show with evidence from this dataset why the
Negative Binomial specification is used instead of simply asserting it.

Model form
----------
    Dengue Cases ~ Poisson(mu)
    log(mu) = intercept + b1 * density + year terms + log(Population)

Population enters as an offset rather than as a predictor. Fixing its
coefficient at one turns the model from a model of counts into a model of rates,
so a large LGU is not judged high risk merely for being large.

Density is expressed in thousands of persons per square kilometre. The raw
figures run from roughly 6,400 to 76,000, and dividing by 1,000 makes the
coefficient readable as the effect of one thousand extra persons per square
kilometre instead of one extra person.

Year enters as a set of dummy variables by default. NCR case totals across the
five years are 10,493 / 43,753 / 23,678 / 37,225 / 45,014, which rise, fall and
rise again. A single linear year term cannot represent that shape, so each year
gets its own term with 2021 as the reference. A linear alternative is available
through ``year_as="numeric"`` for comparison.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

DENSITY_SCALE = 1_000
REFERENCE_YEAR = 2021

REQUIRED_COLUMNS = ["LGU", "Year", "Dengue Cases", "Population", "Population Density"]


def build_design_matrix(panel: pd.DataFrame, year_as: str = "factor") -> pd.DataFrame:
    """Assemble the predictor matrix: intercept, scaled density, and year terms."""
    _validate_panel(panel)

    design = pd.DataFrame(index=panel.index)
    design["Density per 1000"] = panel["Population Density"] / DENSITY_SCALE

    if year_as == "factor":
        # drop_first leaves 2021 as the reference year, so each remaining
        # coefficient reads as that year against 2021.
        dummies = pd.get_dummies(panel["Year"].astype(int), prefix="Year", drop_first=True)
        design = pd.concat([design, dummies.astype(float)], axis=1)
    elif year_as == "numeric":
        design["Year Index"] = panel["Year"].astype(int) - REFERENCE_YEAR
    elif year_as == "none":
        pass
    else:
        raise ValueError(f"year_as must be 'factor', 'numeric' or 'none', got {year_as!r}")

    return sm.add_constant(design, has_constant="add")


def _build_model(panel: pd.DataFrame, year_as: str = "factor"):
    """Assemble the GLM object shared by the Poisson and quasi-Poisson fits."""
    _validate_panel(panel)

    endog = panel["Dengue Cases"].astype(float)
    exog = build_design_matrix(panel, year_as=year_as)
    offset = np.log(panel["Population"].astype(float))

    return sm.GLM(endog, exog, family=sm.families.Poisson(), offset=offset)


def fit_poisson_baseline(panel: pd.DataFrame, year_as: str = "factor"):
    """Fit the Poisson GLM with log(Population) as the exposure offset."""
    return _build_model(panel, year_as=year_as).fit()


def fit_quasi_poisson(panel: pd.DataFrame, year_as: str = "factor"):
    """The same fit with standard errors rescaled by the Pearson dispersion.

    Poisson standard errors assume the variance equals the mean. When the data
    is overdispersed that assumption is false and the reported standard errors
    are too small, which makes every predictor look more precisely estimated
    than it is. Scaling by the Pearson statistic shows how much of the apparent
    precision in the baseline output is an artefact of the wrong variance
    assumption. It is a diagnostic here, not the study's model.
    """
    return _build_model(panel, year_as=year_as).fit(scale="X2")


def overdispersion_index(results) -> float:
    """Pearson chi-square divided by residual degrees of freedom.

    Under a correctly specified Poisson model the conditional variance equals
    the conditional mean and this ratio is close to 1. A value materially above
    1 means the observed variance is larger than Poisson allows, which is the
    condition the Negative Binomial model is designed to handle.
    """
    return float(results.pearson_chi2) / int(results.df_resid)


def deviance_ratio(results) -> float:
    """Residual deviance divided by residual degrees of freedom.

    A second reading of the same question, reported alongside the Pearson index
    so the conclusion does not rest on one statistic.
    """
    return float(results.deviance) / int(results.df_resid)


def overdispersion_report(results) -> dict:
    """Collect both dispersion statistics and a plain reading of them."""
    index = overdispersion_index(results)
    ratio = deviance_ratio(results)

    if index < 1.5:
        verdict = "No material overdispersion; Poisson is adequate"
    elif index < 2:
        verdict = "Mild overdispersion"
    else:
        verdict = "Substantial overdispersion; Negative Binomial is warranted"

    return {
        "observations": int(results.nobs),
        "parameters": int(results.df_model) + 1,
        "df_resid": int(results.df_resid),
        "pearson_chi2": float(results.pearson_chi2),
        "overdispersion_index": index,
        "deviance": float(results.deviance),
        "deviance_ratio": ratio,
        "log_likelihood": float(results.llf),
        "aic": float(results.aic),
        "verdict": verdict,
    }


def coefficient_table(results) -> pd.DataFrame:
    """Coefficients with incidence rate ratios, standard errors and p-values.

    ``exp(coefficient)`` is the multiplicative effect on the expected case rate,
    which is how a Poisson or Negative Binomial coefficient is normally read.
    """
    table = pd.DataFrame(
        {
            "Coefficient": results.params,
            "Std. Error": results.bse,
            "z": results.tvalues,
            "p-value": results.pvalues,
            "Rate Ratio": np.exp(results.params),
            "CI Lower": np.exp(results.conf_int()[0]),
            "CI Upper": np.exp(results.conf_int()[1]),
        }
    )
    table.index.name = "Term"
    return table


def _validate_panel(panel: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in panel.columns]
    if missing:
        raise ValueError(f"Panel is missing required column(s): {missing}")
    if (panel["Population"] <= 0).any():
        raise ValueError("Population must be strictly positive to be used as an offset")
    if (panel["Dengue Cases"] < 0).any():
        raise ValueError("Dengue cases cannot be negative")
