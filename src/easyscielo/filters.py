"""Filter normalizers for SciELO search queries."""

import unicodedata
from datetime import datetime
from typing import Any, Optional, Sequence, Union

from easyscielo.errors import ValidationError

COUNTRY_TO_CODE: dict[str, str] = {
    "Costa Rica": "cri",
    "México": "mex",
    "Brasil": "bra",
    "Colombia": "col",
    "Argentina": "arg",
    "Chile": "chl",
    "Cuba": "cub",
    "Perú": "per",
    "Venezuela": "ven",
    "Uruguay": "ury",
    "Ecuador": "ecu",
    "Paraguay": "pry",
    "Panamá": "pan",
}

ALLOWED_CODES: set[str] = set(COUNTRY_TO_CODE.values())


def _remove_accents(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8")


NORMALIZED_COUNTRY_MAP: dict[str, str] = {
    _remove_accents(name).lower(): code for name, code in COUNTRY_TO_CODE.items()
}

ALLOWED_LANGUAGES: set[str] = {"es", "pt", "en"}


def _to_string_list(val: Any, type_error_msg: str) -> list[str]:
    if isinstance(val, str):
        return [val]
    if isinstance(val, (list, tuple, set)):
        items = list(val)
        if not all(isinstance(item, str) for item in items):
            raise ValidationError(type_error_msg)
        return items
    if isinstance(val, Sequence) and not isinstance(val, (str, bytes, dict)):
        items = list(val)
        if not all(isinstance(item, str) for item in items):
            raise ValidationError(type_error_msg)
        return items
    raise ValidationError(type_error_msg)


def normalize_collections(collections: Union[str, Sequence[str]]) -> list[str]:
    """Normalize SciELO collection names or ISO codes.

    Accepts country names or ISO codes (e.g. 'Costa Rica' or 'cri').
    Matches accent-free and case-insensitively.
    Returns a list of valid ISO codes.
    """
    raw_list = _to_string_list(collections, "'collections' must be a character vector.")
    result: list[str] = []

    valid_names = ", ".join(COUNTRY_TO_CODE.keys())

    for item in raw_list:
        val = item.strip()
        if len(val) < 2:
            raise ValidationError(
                "The provided collection value is too short to be valid."
            )

        val_lower = val.lower()
        if val_lower in ALLOWED_CODES:
            result.append(val_lower)
            continue

        normalized_name = _remove_accents(val).lower()
        if normalized_name in NORMALIZED_COUNTRY_MAP:
            result.append(NORMALIZED_COUNTRY_MAP[normalized_name])
            continue

        raise ValidationError(
            f"Invalid collection: '{val}'. "
            "Please use a valid country name or ISO code. "
            f"Valid values include: {valid_names}."
        )

    return result


def normalize_languages(languages: Union[str, Sequence[str]]) -> list[str]:
    """Normalize and validate article language codes ('es', 'pt', 'en')."""
    raw_list = _to_string_list(
        languages, "The language code must be a character string."
    )
    result: list[str] = []

    for item in raw_list:
        lang_code = item.strip().lower()
        if lang_code not in ALLOWED_LANGUAGES:
            raise ValidationError(
                f"Invalid language code: '{lang_code}'. Allowed values are: es, pt, en."
            )
        result.append(lang_code)

    return result


def normalize_journals(journals: Union[str, Sequence[str]]) -> list[str]:
    """Normalize and validate journal names."""
    raw_list = _to_string_list(journals, "The journal name must be a character string.")
    result: list[str] = []

    for item in raw_list:
        journal = item.strip()
        if len(journal) < 2:
            raise ValidationError(
                "The journal name must be at least 2 characters long."
            )
        result.append(journal)

    return result


def normalize_categories(categories: Union[str, Sequence[str]]) -> list[str]:
    """Normalize and validate subject categories."""
    raw_list = _to_string_list(
        categories, "The subject category must be a character string."
    )
    result: list[str] = []

    for item in raw_list:
        category = item.strip()
        if len(category) < 2:
            raise ValidationError(
                "The subject category must be at least 2 characters long."
            )
        result.append(category)

    return result


def normalize_years(
    start: Optional[Union[int, str]] = None,
    end: Optional[Union[int, str]] = None,
) -> tuple[Optional[int], Optional[int]]:
    """Validate year range for SciELO query.

    Requires both start and end years, or neither (both None).
    Years must be integers between 1500 and the current year, in correct order.
    """
    if start is None and end is None:
        return (None, None)

    if start is None or end is None:
        raise ValidationError("Both 'start_year' and 'end_year' must be provided.")

    start_year = _parse_year_int(start, "start_year")
    end_year = _parse_year_int(end, "end_year")

    current_year = datetime.now().year

    if start_year < 1500 or start_year > current_year:
        raise ValidationError(f"'start_year' must be between 1500 and {current_year}.")

    if end_year < 1500 or end_year > current_year:
        raise ValidationError(f"'end_year' must be between 1500 and {current_year}.")

    if start_year > end_year:
        raise ValidationError("'start_year' must be less than or equal to 'end_year'.")

    return (start_year, end_year)


def _parse_year_int(val: Any, name: str) -> int:
    if isinstance(val, bool):
        raise ValidationError(f"'{name}' must be an integer number.")
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
            return int(val_str)
    raise ValidationError(f"'{name}' must be an integer number.")


def normalize_n_max(value: Optional[Union[int, str]] = None) -> Optional[int]:
    """Normalize and validate n_max (must be a positive integer or None)."""
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValidationError(
            "The 'n_max' parameter must be a positive numeric value or NULL."
        )

    parsed_val: Optional[int] = None
    if isinstance(value, int):
        parsed_val = value
    elif isinstance(value, str):
        val_str = value.strip()
        if val_str.isdigit():
            parsed_val = int(val_str)

    if parsed_val is None or parsed_val <= 0:
        raise ValidationError(
            "The 'n_max' parameter must be a positive numeric value or NULL."
        )

    return parsed_val


normalize_nmax = normalize_n_max
