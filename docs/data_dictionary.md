# Data Dictionary

Covers `data/04_validated/lgu_year_panel.csv` (the 85-row LGU-year analytical
panel), its upstream component `data/03_processed/population_panel.csv`, and the
derived indicator columns exported to `outputs/dashboard_exports/`.

---

## Panel variables

### LGU
- **Meaning:** One of the 17 cities/municipalities of Metro Manila (NCR)
- **Source:** DOH–MMCHD (FOI) / PSA
- **Unit:** categorical
- **Transformation:** Standardized to a canonical short form via `src/lgu_names.py` (handles PSA official form, suffixes, the Kalookan variant, and missing tildes)
- **Analytical role:** Panel identifier / geographic unit
- **Status tag:** official

### Year
- **Meaning:** Calendar year of observation
- **Source:** DOH–MMCHD (FOI) / PSA
- **Unit:** categorical, 2021–2025
- **Transformation:** None
- **Analytical role:** Time index for the panel
- **Status tag:** official

### Dengue Cases
- **Meaning:** Total annual dengue case count for the LGU-year
- **Source:** DOH–MMCHD (via FOI)
- **Unit:** count
- **Transformation:** None — reported as released
- **Analytical role:** Dependent variable in the NB/Poisson regression; basis for incidence rate
- **Status tag:** official

### Population
- **Meaning:** Estimated total population for the LGU-year
- **Source:** PSA 2020 Census (anchor) and PSA 2024 POPCEN (anchor); 2021–2023 and 2025 derived
- **Unit:** count
- **Transformation:** 2020, 2024 — taken directly from PSA source. 2021–2023 — linear interpolation between the 2020 and 2024 anchors. 2025 — linear extrapolation using the same growth rate beyond the 2024 anchor
- **Analytical role:** Exposure/offset term in the regression; denominator for incidence rate and density
- **Status tag:** official (2020, 2024) / interpolated (2021–2023) / extrapolated (2025)

### Land Area
- **Meaning:** Fixed land area of the LGU
- **Source:** PSA (2013 land area reference, consistent across the 2020 and 2024 releases)
- **Unit:** km²
- **Transformation:** None — verified identical between the 2020 and 2024 source files; carried forward unchanged across all 5 years
- **Analytical role:** Denominator for population density
- **Status tag:** official

### Population Density
- **Meaning:** Population per square kilometre for the LGU-year
- **Source:** Computed
- **Unit:** persons/km²
- **Transformation:** `Population ÷ Land Area`, recomputed for every year using that year's estimated population
- **Analytical role:** Primary structural predictor in the NB/Poisson regression
- **Status tag:** computed (inherits the status of the Population value used)

### Incidence Rate
- **Meaning:** Dengue cases per 100,000 population for the LGU-year
- **Source:** Computed
- **Unit:** cases per 100,000
- **Transformation:** `Dengue Cases ÷ Population × 100,000`
- **Analytical role:** Descriptive indicator for cross-LGU comparison; basis for the five-year-average trend indicator
- **Status tag:** computed (inherits the status of the Population value used)

### Previous Year Incidence
- **Meaning:** The same LGU's incidence rate in the preceding year
- **Source:** Computed
- **Unit:** cases per 100,000
- **Transformation:** Incidence Rate shifted by one year within the LGU, after sorting by LGU then Year. Empty for 2021, which has no prior year in the panel
- **Analytical role:** Denominator of the year-over-year change; carried in the export so the change can be audited without a second lookup
- **Status tag:** computed

### YoY % Change
- **Meaning:** Percent change in incidence against the same LGU's previous year
- **Source:** Computed
- **Unit:** percent
- **Transformation:** `(Incidence Rate - Previous Year Incidence) / Previous Year Incidence x 100`. Always within one LGU, never across LGUs. Empty for 2021
- **Analytical role:** Descriptive year-on-year movement for the trend view of the dashboard
- **Status tag:** computed (inherits the status of the two Population values used)

### Five-Year Average Incidence
- **Meaning:** The LGU's own mean incidence across 2021-2025
- **Source:** Computed
- **Unit:** cases per 100,000
- **Transformation:** Plain mean of that LGU's five annual incidence values, broadcast to all five of its rows
- **Analytical role:** Within-LGU benchmark; the 2025 comparison against it is the second condition of the three-tier priority rule
- **Status tag:** computed

### At or Above Average
- **Meaning:** Whether the LGU's 2025 incidence is at or above its own five-year average
- **Source:** Computed
- **Unit:** boolean
- **Transformation:** `2025 Incidence >= Five-Year Average Incidence`, evaluated on unrounded values
- **Analytical role:** Second of the two conditions in the three-tier priority rule. Present in `outputs/dashboard_exports/lgu_summary_2025.csv` at LGU grain, not in the LGU-year panel
- **Status tag:** computed

### Status
- **Meaning:** Confidence/provenance tag for the Population value used in that row
- **Source:** Derived
- **Unit:** categorical
- **Transformation:** `official` if Year is 2020 or 2024; `interpolated` if strictly between; `extrapolated` if beyond 2024
- **Analytical role:** Disclosure field — flags which years' density/incidence values are lower-confidence (extrapolated) for the dashboard and discussion
- **Status tag:** descriptive

---

## Excluded from the panel (used descriptively only)

### Age Group
- **Meaning:** Dengue case counts by age band, aggregated at the NCR level
- **Source:** DOH–MMCHD (via FOI)
- **Unit:** count, by age band
- **Transformation:** None
- **Analytical role:** Descriptive profile of dengue cases NCR-wide; not an LGU-level predictor
- **Status tag:** descriptive

### Sex
- **Meaning:** Dengue case counts by sex, aggregated at the NCR level
- **Source:** DOH–MMCHD (via FOI)
- **Unit:** count, by sex
- **Transformation:** None
- **Analytical role:** Descriptive profile of dengue cases NCR-wide; not an LGU-level predictor
- **Status tag:** descriptive

Age and sex data are excluded from the regression because they are released only
at the NCR level, not disaggregated by LGU — including them as LGU-level
predictors would mismatch the unit of analysis used throughout the rest of the
panel. They are retained for the dashboard's descriptive age-sex panel only.

---

## Status tag definitions

- **official** — value taken directly from an official government source (DOH–MMCHD or PSA) with no transformation.
- **interpolated** — value estimated for a year *between* two known official reference points (2020 and 2024), using linear interpolation. Bounded by real data on both sides.
- **extrapolated** — value estimated for a year *beyond* the last known official reference point (2025), using the same linear growth rate projected forward. Carries more uncertainty than interpolation since no second anchor constrains it; flagged as lower-confidence in the dashboard and in this documentation.
- **computed** — value derived arithmetically from other panel variables (density, incidence rate). Its confidence level is inherited from the Population value used in that row.
- **descriptive** — value used for context/description only, not as a model input.
