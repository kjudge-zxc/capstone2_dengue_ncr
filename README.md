# Dengue Risk Estimation and LGU Prioritization in Metro Manila

MO-IT200D2 Capstone 2 | Section A4103 | Group 1
Mapúa Malayan Digital College

**Members:** Rania Nabil M. Abdelfattah, Martin Sheen C. Cajucom, Chadley Marie V. De Lara, Karissa Mae T. Manicad

**Mentor:** John Edmon Alcomendas

Annual dengue analytics and LGU prioritization for the 17 LGUs of Metro Manila (2021–2025), using Negative Binomial panel regression and a Tableau dashboard.

## Data

All data used in this project is aggregated, de-identified secondary data obtained from official government sources: the DOH Metro Manila Center for Health Development (via Freedom of Information request) and the Philippine Statistics Authority. No individually identifiable patient data is collected or processed.

## Structure
| Path | Contents |
|---|---|
| `data/01_raw/` | FOI source PDF and transcribed CSVs — never edited |
| `data/02_official_reference/` | PSA census and land area |
| `data/03_processed/` | Cleaned and transformed datasets |
| `data/04_validated/` | Validated 85-row LGU-year panel |
| `outputs/analytical/` | Regression outputs and diagnostics |
| `outputs/dashboard_exports/` | Tableau-ready CSVs |
| `docs/` | Data dictionary, methodology notes |
| `notebooks/` | Analysis notebooks |
| `src/` | Pipeline functions |
| `tests/` | pytest suite |

## Setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
