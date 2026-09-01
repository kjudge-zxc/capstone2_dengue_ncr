# Calculation Validation — Round 1

**Purpose.** Confirm that the automated pipeline (`src/population.py`, `src/panel.py`)
reproduces values that match independent, by-hand recomputation using only the raw
source CSVs and plain arithmetic — no pipeline code was reused in the hand
calculation below.

**Method.** For each sampled LGU-year:

1. Population was recomputed from the raw 2020/2024 PSA figures using
   `P(t) = P0 + (P1 - P0) * (t - 2020) / (2024 - 2020)` for interpolated/extrapolated
   years, or read directly from the source file for 2024.
2. Density was recomputed as `Population / Land Area`, using the land area from
   the raw 2020 reference file.
3. Incidence rate was recomputed as `Dengue Cases / Population * 100,000`, using
   the raw FOI case count for that LGU-year.
4. Each hand-computed value was compared against the corresponding value in
   `data/04_validated/lgu_year_panel.csv`.

**Sample.** Five LGU-years were selected to cover all three population status
types and a range of LGU sizes: Quezon City 2021 (interpolated), Manila 2024
(official), Pateros 2025 (extrapolated), Taguig 2023 (interpolated), Malabon
2025 (extrapolated).

---

## Results

### Quezon City — 2021 (interpolated)
- Population — hand: 2,991,103.50 | pipeline: 2,991,103.50 | matches
- Density — hand: 17,419.51 | pipeline: 17,419.51 | matches
- Incidence Rate — hand: 55.06 | pipeline: 55.06 | matches

### Manila — 2024 (official)
- Population — hand: 1,902,590.00 | pipeline: 1,902,590.00 | matches
- Density — hand: 76,164.53 | pipeline: 76,164.53 | matches
- Incidence Rate — hand: 289.66 | pipeline: 289.66 | matches

### Pateros — 2025 (extrapolated)
- Population — hand: 67,842.00 | pipeline: 67,842.00 | matches
- Density — hand: 6,523.27 | pipeline: 6,523.27 | matches
- Incidence Rate — hand: 347.87 | pipeline: 347.87 | matches

### Taguig — 2023 (interpolated)
- Population — hand: 1,202,744.25 | pipeline: 1,202,744.25 | matches
- Density — hand: 26,603.50 | pipeline: 26,603.50 | matches
- Incidence Rate — hand: 222.99 | pipeline: 222.99 | matches

### Malabon — 2025 (extrapolated)
- Population — hand: 392,280.75 | pipeline: 392,280.75 | matches
- Density — hand: 24,970.13 | pipeline: 24,970.13 | matches
- Incidence Rate — hand: 343.89 | pipeline: 343.89 | matches

---

All five sampled LGU-years matched hand-computed values exactly (tolerance <0.01, attributable only to floating point display rounding).

**Note on Manila (2024, official).** The 2024 figure is read directly from the
PSA source file rather than derived from the interpolation/extrapolation formula,
per the study's design — the hand recomputation confirms the pipeline does not
silently recompute or otherwise alter official-year figures.

**Note on Pateros and Malabon (extrapolated).** These confirm the extrapolation
formula is applied consistently to both a small LGU (Pateros) and a mid-sized
LGU (Malabon), and that the same linear formula used for interpolation is what
drives the 2025 extrapolation, per the study's design.

**Conclusion.** This calculation validation round finds no discrepancies. This validates the correctness
of `estimate_population()`, `compute_density()`, and the incidence rate
computation in `build_lgu_year_panel()` against an independent manual recomputation.
Reproducible via `notebooks/02_population_and_panel_construction.ipynb`.
