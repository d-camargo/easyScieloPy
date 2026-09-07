"""Configuration utilities for easyscielo API integrations."""

import os
import warnings

_WARNED_SOURCES: set[str] = set()


def _resolve_config(explicit: str | None, env_var: str) -> str | None:
    """Resolve config value by checking explicit argument -> env var -> None."""
    if explicit:
        return explicit
    val = os.getenv(env_var)
    if val:
        return val
    return None


def openalex_email(explicit: str | None = None) -> str | None:
    """Get OpenAlex contact email from explicit arg, OPENALEX_EMAIL env, or None."""
    return _resolve_config(explicit, "OPENALEX_EMAIL")


def openalex_api_key(explicit: str | None = None) -> str | None:
    """Get OpenAlex API key from explicit arg, OPENALEX_API_KEY env, or None."""
    return _resolve_config(explicit, "OPENALEX_API_KEY")


def crossref_mailto(explicit: str | None = None) -> str | None:
    """Get CrossRef mailto contact from explicit arg, CROSSREF_MAILTO env, or None."""
    return _resolve_config(explicit, "CROSSREF_MAILTO")


def redact(secret: str | None) -> str:
    """Redact sensitive secret strings.

    Returns '***' for empty or short values (<= 8 chars).
    For longer values, returns 'abcd…wxyz' (4 first + 4 last characters).
    """
    if not secret or len(secret) <= 8:
        return "***"
    return f"{secret[:4]}…{secret[-4:]}"


def warn_no_contact(source_name: str) -> None:
    """Emit UserWarning once per process for missing contact email."""
    if source_name in _WARNED_SOURCES:
        return
    _WARNED_SOURCES.add(source_name)
    warnings.warn(
        f"Sem e-mail para {source_name}, a requisição cai no pool comum.",
        UserWarning,
        stacklevel=2,
    )
