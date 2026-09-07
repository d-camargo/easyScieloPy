"""Optional dependencies helper."""

import importlib
from types import ModuleType


def require(module: str, extra: str) -> ModuleType:
    """Import an optional module or raise ImportError with installation instructions."""
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise ImportError(
            f"{module} is required for this feature. "
            f"Please install it using 'pip install easyscielopy[{extra}]'."
        ) from e
