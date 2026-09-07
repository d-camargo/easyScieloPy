import pytest

from easyscielo.backends import BackendError, get_backend
from easyscielo.backends.base import Backend


def test_get_backend_valid():
    """Test that valid backend names return a Backend instance."""
    for name in ["search", "articlemeta", "oai"]:
        backend = get_backend(name)
        assert isinstance(backend, Backend)
        assert backend.name == name


def test_get_backend_invalid():
    """Test that invalid backend names raise BackendError with valid names."""
    with pytest.raises(BackendError) as exc_info:
        get_backend("invalid_name")

    error_msg = str(exc_info.value)
    assert "invalid_name" in error_msg
    assert "search" in error_msg
    assert "articlemeta" in error_msg
    assert "oai" in error_msg
