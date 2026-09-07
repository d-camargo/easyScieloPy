import types

import pytest

from easyscielo._optional import require


def test_require_existing_module():
    mod = require("json", "json_extra")
    assert isinstance(mod, types.ModuleType)
    assert mod.__name__ == "json"


def test_require_missing_module():
    with pytest.raises(ImportError) as exc_info:
        require("nonexistent_module_xyz_123", "myextra")

    msg = str(exc_info.value)
    assert "nonexistent_module_xyz_123 is required for this feature." in msg
    assert "pip install easyscielopy[myextra]" in msg
