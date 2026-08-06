from typing import Any

import pytest

from iokit import Json


def test_encryption() -> None:
    data: dict[str, Any] = {
        "list": [1, 2, 3],
        "tuple": (4, 5, 6),
        "dict": {"a": 1, "b": 2},
        "str": "hello",
        "int": 42,
    }
    json = Json(data, path="different.json")
    state = json.encrypt(password="pA$sw0Rd", salt="s@lt")
    assert state.path == "different.json.enc"
    with pytest.raises(ValueError) as excinfo:
        state.load(password="pA$sw0Rd")
    assert str(excinfo.value) == "Decryption failed"
    with pytest.raises(ValueError) as excinfo:
        state.load(password="password", salt="s@lt")
    assert str(excinfo.value) == "Decryption failed"

    state_loaded = state.load(password="pA$sw0Rd", salt="s@lt")
    assert state_loaded.name == "different.json"
    loaded = state_loaded.load()
    assert all(v1 == v2 for v1, v2 in zip(loaded["list"], [1, 2, 3], strict=True))
    assert all(v1 == v2 for v1, v2 in zip(loaded["tuple"], (4, 5, 6), strict=True))
    assert loaded["dict"] == {"a": 1, "b": 2}
    assert loaded["str"] == "hello"
    assert loaded["int"] == 42
