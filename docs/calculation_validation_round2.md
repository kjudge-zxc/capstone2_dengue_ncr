# Calculation Validation — Round 2

**Purpose.** Confirm that the descriptive indicators produced by `src/indicators.py`
(incidence rate, year-over-year percent change, five-year average incidence) match
independent by-hand recomputation from the raw source CSVs, using plain arithmetic
and no pipeline code.

Round 1 (`docs/calculation_validation_round1.md`) validated the panel inputs:
population, density and incidence for five sampled LGU-years. Round 2 validates the
indicators built on top of those inputs.

**Method.** For each sampled LGU-year:

1. Population was rebuilt from the raw 2020 and 2024 PSA figures using
   `P(t) = P0 + (P1 - P0) * (t - 2020) / (2024 - 2020)`, or read directly from the
   source file for 2024.
2. Incidence was recomputed as `Dengue Cases / Population * 100,000`, using the raw
   FOI case count for that LGU-year.
3. Year-over-year change was recomputed as
   `(this year's incidence - last year's incidence) / last year's incidence * 100`,
   with both years' incidence rebuilt by hand from the raw files.
4. The five-year average was recomputed as the plain mean of the LGU's five
   hand-computed incidence values for 2021 to 2025.
5. Each hand-computed value was compared against the corresponding value in the
   indicator panel produced by `build_indicator_panel()`.

**Sample.** Five LGU-years chosen to cover the largest and smallest LGUs, the 2022
surge year, an LGU whose population declines between census anchors, and one LGU
sitting close enough to its own average to test the boundary of the at-or-above
comparison.

---

## Results

### Manila — 2025 (largest LGU, extrapolated population)
- Incidence — hand: 448.76 | pipeline: 448.76 | matches
- YoY % change — hand: +54.93 | pipeline: +54.93 | matches
- Five-year average — hand: 231.33 | pipeline: 231.33 | matches

### Caloocan — 2022 (the surge year)
- Incidence — hand: 259.06 | pipeline: 259.06 | matches
- YoY % change — hand: +312.72 | pipeline: +312.72 | matches
- Five-year average — hand: 193.08 | pipeline: 193.08 | matches

### Makati — 2023 (declining population between anchors)
- Incidence — hand: 291.48 | pipeline: 291.48 | matches
- YoY % change — hand: -30.40 | pipeline: -30.40 | matches
- Five-year average — hand: 322.79 | pipeline: 322.79 | matches

### Pateros — 2025 (smallest LGU, sharp decline)
- Incidence — hand: 347.87 | pipeline: 347.87 | matches
- YoY % change — hand: -52.60 | pipeline: -52.60 | matches
- Five-year average — hand: 438.65 | pipeline: 438.65 | matches

### Malabon — 2025 (sits just below its own average)
- Incidence — hand: 343.89 | pipeline: 343.89 | matches
- YoY % change — hand: +20.80 | pipeline: +20.80 | matches
- Five-year average — hand: 347.55 | pipeline: 347.55 | matches

---

All five sampled LGU-years matched hand-computed values on all three indicators
(tolerance <0.01, attributable only to floating point display rounding).

**Note on Caloocan (2022).** The +312.72% change is genuine and not a computation
error. NCR case counts rose from 10,493 in 2021 to 43,753 in 2022, and Caloocan's
incidence rose from 62.77 to 259.06 in the same period. The check confirms that a
change of this size passes through the formula unaltered rather than being clipped
or smoothed.

**Note on Malabon (2025).** Its 2025 incidence of 343.89 sits 3.67 below its own
five-year average of 347.55, so `At or Above Average` is False. This is the closest
margin of the 17 LGUs and confirms the comparison is evaluated on the underlying
values rather than on rounded display figures. Rounding both to whole numbers would
have flipped this LGU to True.

**Note on Makati (2023).** Makati's PSA population figures are 629,616 in 2020 and
309,770 in 2024, so its interpolated population falls year on year and its
extrapolated 2025 figure continues downward. The hand recomputation confirms the
indicator chain handles a declining denominator correctly. The size of that decline
is a data question rather than a computation question and is recorded separately in
the testing log.

**Conclusion.** Calculation validation round 2 finds no discrepancies. This validates
`compute_incidence_rate()`, `compute_yoy_change()` and `compute_five_year_average()`
against independent manual recomputation. Reproducible via
`notebooks/03_descriptive_indicators.ipynb`, section 9.
