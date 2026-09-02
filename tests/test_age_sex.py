import pandas as pd
import pytest
from pathlib import Path

from src.age_sex import (
    load_age_sex_tables,
    build_age_summary,
    build_sex_summary,
    build_pooled_age_profile,
    summarise_child_share,
)
from src.validation import AGE_GROUPS, FOI_GRAND_TOTALS, YEARS

RAW = Path(__file__).parent.parent / "data" / "01_raw"


@pytest.fixture
def tables():
    return load_age_sex_tables(RAW)


@pytest.fixture
def age_summary(tables):
    return build_age_summary(tables)


def test_all_five_years_load(tables):
    assert sorted(tables.keys()) == YEARS


def test_age_summary_has_13_bands_for_each_of_5_years(age_summary):
    assert len(age_summary) == 13 * 5
    for year, group in age_summary.groupby("Year"):
        assert group["Age Group"].tolist() == AGE_GROUPS


def test_age_summary_totals_match_the_foi_grand_totals(age_summary):
    per_year = age_summary.groupby("Year")["Total"].sum()
    for year in YEARS:
        assert int(per_year[year]) == FOI_GRAND_TOTALS[year]


def test_female_plus_male_equals_total_in_every_row(age_summary):
    assert (age_summary["Female"] + age_summary["Male"] == age_summary["Total"]).all()


def test_shares_sum_to_100_within_each_year(age_summary):
    for year, group in age_summary.groupby("Year"):
        assert group["Share of Year %"].sum() == pytest.approx(100.0)


def test_grand_total_row_is_excluded(age_summary):
    assert "Grand Total" not in age_summary["Age Group"].tolist()


def test_age_summary_rejects_a_table_that_does_not_reconcile(tables):
    tampered = {year: table.copy() for year, table in tables.items()}
    tampered[2023].loc[0, "Grand Total"] = tampered[2023].loc[0, "Grand Total"] + 100
    with pytest.raises(ValueError):
        build_age_summary(tampered)


def test_age_summary_rejects_a_missing_age_band(tables):
    tampered = {year: table.copy() for year, table in tables.items()}
    tampered[2022] = tampered[2022].drop(index=3)
    with pytest.raises(ValueError):
        build_age_summary(tampered)


# --- sex summary ------------------------------------------------------------

def test_sex_summary_has_one_row_per_year(tables):
    summary = build_sex_summary(tables)
    assert summary["Year"].tolist() == YEARS


def test_sex_shares_sum_to_100(tables):
    summary = build_sex_summary(tables)
    assert (summary["Female %"] + summary["Male %"]).round(9).eq(100.0).all()


def test_sex_totals_match_the_foi_grand_totals(tables):
    summary = build_sex_summary(tables).set_index("Year")
    for year in YEARS:
        assert int(summary.loc[year, "Total"]) == FOI_GRAND_TOTALS[year]


# --- pooled profile and child share ----------------------------------------

def test_pooled_profile_keeps_age_bands_in_order(age_summary):
    pooled = build_pooled_age_profile(age_summary)
    assert pooled["Age Group"].tolist() == AGE_GROUPS


def test_pooled_profile_totals_equal_the_sum_of_all_five_years(age_summary):
    pooled = build_pooled_age_profile(age_summary)
    assert int(pooled["Total"].sum()) == sum(FOI_GRAND_TOTALS.values())
    assert pooled["Share of All Years %"].sum() == pytest.approx(100.0)


def test_child_share_is_between_0_and_100(age_summary):
    shares = summarise_child_share(age_summary)
    assert len(shares) == 5
    assert shares["Share %"].between(0, 100).all()


def test_child_share_matches_a_hand_sum_for_one_year(age_summary):
    year = 2025
    rows = age_summary[age_summary["Year"] == year]
    hand = rows[rows["Age Group"].isin(["0-4", "5-9", "10-14"])]["Total"].sum()
    computed = summarise_child_share(age_summary).set_index("Year").loc[year]
    assert computed["Total in Bands"] == hand
    assert computed["Share %"] == pytest.approx(hand / FOI_GRAND_TOTALS[year] * 100)
