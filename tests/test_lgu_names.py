import pytest

from src.lgu_names import CANONICAL_LGUS, normalize_lgu_name, normalize_lgu_series

# Name formats actually present in the project's three source files
FOI_DENGUE_NAMES = [
    "Caloocan", "Las Piñas", "Makati", "Malabon", "Mandaluyong", "Manila",
    "Marikina", "Muntinlupa", "Navotas", "Parañaque", "Pasay City", "Pasig",
    "Pateros", "Quezon City", "San Juan", "Taguig", "Valenzuela",
]

# PSA official convention, for future joins to PSA tables or shapefiles
PSA_OFFICIAL_NAMES = [
    "CITY OF CALOOCAN", "CITY OF LAS PIÑAS", "CITY OF MAKATI", "CITY OF MALABON",
    "CITY OF MANDALUYONG", "CITY OF MANILA", "CITY OF MARIKINA",
    "CITY OF MUNTINLUPA", "CITY OF NAVOTAS", "CITY OF PARAÑAQUE", "PASAY CITY",
    "PASIG CITY", "PATEROS", "QUEZON CITY", "CITY OF SAN JUAN", "TAGUIG CITY",
    "CITY OF VALENZUELA",
]


def test_canonical_list_has_17_lgus():
    assert len(CANONICAL_LGUS) == 17
    assert len(set(CANONICAL_LGUS)) == 17


def test_foi_source_names_all_resolve():
    assert sorted(normalize_lgu_series(FOI_DENGUE_NAMES)) == sorted(CANONICAL_LGUS)


def test_psa_official_names_all_resolve():
    assert sorted(normalize_lgu_series(PSA_OFFICIAL_NAMES)) == sorted(CANONICAL_LGUS)


def test_pasay_city_suffix_is_dropped():
    assert normalize_lgu_name("Pasay City") == "Pasay"


def test_quezon_city_keeps_its_suffix():
    assert normalize_lgu_name("Quezon City") == "Quezon City"
    assert normalize_lgu_name("QUEZON") == "Quezon City"


def test_kalookan_variant_maps_to_caloocan():
    assert normalize_lgu_name("Kalookan") == "Caloocan"
    assert normalize_lgu_name("KALOOKAN CITY") == "Caloocan"


@pytest.mark.parametrize(
    "given,expected",
    [
        ("Paranaque", "Parañaque"),      # tilde dropped
        ("PARAÑAQUE", "Parañaque"),
        ("Las Pinas", "Las Piñas"),
        ("LAS PIÑAS CITY", "Las Piñas"),
    ],
)
def test_tilde_and_case_variants(given, expected):
    assert normalize_lgu_name(given) == expected


@pytest.mark.parametrize(
    "given", ["  Makati  ", "makati", "MAKATI", "City of Makati", "Makati City"]
)
def test_whitespace_case_and_affix_variants(given):
    assert normalize_lgu_name(given) == "Makati"


def test_pateros_is_a_municipality_not_a_city():
    assert normalize_lgu_name("Pateros") == "Pateros"
    assert normalize_lgu_name("Municipality of Pateros") == "Pateros"


def test_normalization_is_idempotent():
    for lgu in CANONICAL_LGUS:
        assert normalize_lgu_name(lgu) == lgu


@pytest.mark.parametrize("given", ["Cebu City", "Bulacan", "", "   ", None, "NCR"])
def test_unknown_names_raise(given):
    with pytest.raises(ValueError):
        normalize_lgu_name(given)