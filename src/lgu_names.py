"""LGU name standardisation for the 17 local government units of Metro Manila.

The study uses a short canonical form (e.g. "Manila", "Pasay") rather than the PSA
official form (e.g. "CITY OF MANILA", "PASAY CITY"). Since the scope is limited to
NCR, the "City of" prefix carries no disambiguating information, and the short form
reads better as a dashboard label.

"Quezon City" retains its suffix because "City" is part of the name itself, not a
descriptor.
"""

import re
import unicodedata

# The 17 LGUs of NCR: 16 highly urbanised cities plus the municipality of Pateros.
CANONICAL_LGUS = [
    "Caloocan",
    "Las Piñas",
    "Makati",
    "Malabon",
    "Mandaluyong",
    "Manila",
    "Marikina",
    "Muntinlupa",
    "Navotas",
    "Parañaque",
    "Pasay",
    "Pasig",
    "Pateros",
    "Quezon City",
    "San Juan",
    "Taguig",
    "Valenzuela",
]

# Lookup keyed by the stripped, accent-folded, uppercased base name.
_LOOKUP = {
    "CALOOCAN": "Caloocan",
    "KALOOKAN": "Caloocan",       # older DOH/COMELEC spelling
    "LAS PINAS": "Las Piñas",
    "MAKATI": "Makati",
    "MALABON": "Malabon",
    "MANDALUYONG": "Mandaluyong",
    "MANILA": "Manila",
    "MARIKINA": "Marikina",
    "MUNTINLUPA": "Muntinlupa",
    "NAVOTAS": "Navotas",
    "PARANAQUE": "Parañaque",
    "PASAY": "Pasay",
    "PASIG": "Pasig",
    "PATEROS": "Pateros",
    "QUEZON": "Quezon City",
    "SAN JUAN": "San Juan",
    "TAGUIG": "Taguig",
    "VALENZUELA": "Valenzuela",
}

_PREFIXES = ("CITY OF ", "MUNICIPALITY OF ")
_SUFFIXES = (" CITY", " MUNICIPALITY")


def _fold(text: str) -> str:
    """Uppercase, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[.,]", "", text)
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def normalize_lgu_name(name: str) -> str:
    """Map any recognised spelling of an NCR LGU to its canonical short form.

    Handles PSA official form ("CITY OF MANILA"), trailing suffixes ("Pasay City"),
    the Kalookan variant, missing tildes ("Paranaque"), and stray whitespace or case.

    Raises ValueError if the name is not one of the 17 NCR LGUs, so that unmatched
    records fail loudly rather than propagating into the panel.
    """
    if name is None:
        raise ValueError("LGU name is missing")

    key = _fold(name)
    if not key:
        raise ValueError("LGU name is empty")

    for prefix in _PREFIXES:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break

    for suffix in _SUFFIXES:
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break

    key = key.strip()

    if key not in _LOOKUP:
        raise ValueError(f"Unrecognised LGU name: {name!r} (normalised to {key!r})")

    return _LOOKUP[key]


def normalize_lgu_series(values) -> list:
    """Normalise an iterable of LGU names. Convenience wrapper for DataFrame columns."""
    return [normalize_lgu_name(v) for v in values]