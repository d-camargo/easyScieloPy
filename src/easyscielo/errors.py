"""Exceptions hierarchy for easyscielo."""


class ScieloError(Exception):
    """Base exception for all easyscielo errors."""

    pass


class BlockedError(ScieloError):
    """Raised when the SciELO server returns HTTP 403 (blocked/forbidden)."""

    pass


class ParseError(ScieloError):
    """Raised when there is an error parsing data from SciELO."""

    pass


class BackendError(ScieloError):
    """Raised when the SciELO server returns an error (e.g. 500) or fails."""

    pass


class ValidationError(ScieloError):
    """Raised when input parameters (like queries) are invalid."""

    pass
