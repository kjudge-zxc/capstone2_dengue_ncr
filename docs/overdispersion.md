# Overdispersion Check — Poisson Baseline

**Purpose.** Establish from this dataset, rather than by assertion, why the study
uses Negative Binomial regression instead of Poisson.

## Baseline model

```
Dengue Cases ~ Poisson(mu)
log(mu) = intercept + b1 * density (per 1,000/km2) + year dummies + log(Population)
```

- 85 LGU-year observations, 6 estimated parameters, 79 residual degrees of freedom.
- `log(Population)` enters as an offset, with its coefficient fixed at 1, so the
  model estimates rates rather than counts.
- Year enters as dummies with 2021 as the reference, because NCR case totals rise,
  fall and rise again across the five years (10,493 / 43,753 / 23,678 / 37,225 /
  45,014) and a single linear term cannot represent that shape.

Fitted in `notebooks/04_poisson_baseline_and_overdispersion.ipynb` via
`src/models.fit_poisson_baseline()`.

## The test

Poisson regression assumes the conditional variance equals the conditional mean.
The overdispersion index tests that assumption directly:

```
overdispersion index = Pearson chi-square / residual degrees of freedom
```

A correctly specified Poisson model gives an index near 1. Values above 1 mean the
data varies more than Poisson allows.

## Result

| Statistic | Value |
|---|---|
| Pearson chi-square | 15,716.91 |
| Residual degrees of freedom | 79 |
| **Overdispersion index** | **198.95** |
| Residual deviance | 14,683.08 |
| Deviance / df | 185.86 |
| Log-likelihood | -7,718.59 |
| AIC | 15,449.18 |

The index of 198.95 is roughly 199 times the value expected under a correct Poisson
specification. The deviance ratio of 185.86 agrees, so the finding does not rest on
one statistic. The raw counts tell the same story: the variance of the 85 case counts
is about 2,401 times their mean, where Poisson would put the two roughly equal.

**Verdict: substantial overdispersion. The Poisson variance assumption does not hold
for this data, and the Negative Binomial specification is warranted.**

This is the expected result for annual dengue counts. Cases cluster in space and time,
one outbreak seeds the next, and reporting intensity varies between LGUs and years,
all of which produce years far above and far below an LGU's own typical level.

## Effect on the baseline standard errors

Overdispersion does not bias the Poisson coefficients, which remain consistent. It
attacks the standard errors, which are computed under a variance assumption the data
does not satisfy and therefore come out too small.

Rescaling by the Pearson dispersion multiplies every standard error by
`sqrt(198.95) = 14.10`:

| Term | Coefficient | SE (Poisson) | SE (scaled) | p (Poisson) | p (scaled) |
|---|---|---|---|---|---|
| Intercept | -7.1200 | 0.0104 | 0.1472 | <0.001 | <0.001 |
| Density per 1,000/km2 | -0.0017 | 0.0001 | 0.0018 | <0.001 | 0.359 |
| Year 2022 | 1.4188 | 0.0109 | 0.1533 | <0.001 | <0.001 |
| Year 2023 | 0.7960 | 0.0117 | 0.1654 | <0.001 | <0.001 |
| Year 2024 | 1.2399 | 0.0111 | 0.1559 | <0.001 | <0.001 |
| Year 2025 | 1.4215 | 0.0108 | 0.1529 | <0.001 | <0.001 |

The year terms survive the correction. The density term does not: its p-value moves
from below 0.001 to 0.359 once the standard error reflects the actual variance in the
data. **No p-value from the Poisson baseline is reported as a finding of this study.**
Whether density is a statistically detectable predictor is settled by the Negative
Binomial fit, which models the extra variance directly instead of correcting for it
afterwards.

The negative sign on the density coefficient is also recorded here as an observation
from the baseline fit, to be confirmed or revised under the Negative Binomial
specification and discussed in the results chapter either way.

## What follows

The Negative Binomial model estimates a dispersion parameter alpha, where Poisson is
the special case alpha = 0. The formal comparison between the two models is a
likelihood ratio test on that parameter, reported with the Negative Binomial fit.
This document establishes the prior finding that motivates fitting it.
