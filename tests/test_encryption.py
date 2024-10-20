from typing import Any

import pytest

from iokit import Encryption, Json


def test_encryption() -> None:
    data: dict[str, Any] = {
        "list": [1, 2, 3],
        "tuple": (4, 5, 6),
        "dict": {"a": 1, "b": 2},
        "str": "hello",
        "int": 42,
    }
    json = Json(data, name="different")
    state = Encryption(json, password="pA$sw0Rd", salt="s@lt")
    state_secret = state.load()
    with pytest.raises(Exception):
        state_secret.load(password="pA$sw0Rd")
    with pytest.raises(Exception):
        state_secret.load(password="password", salt="s@lt")

    state_loaded = state_secret.load(password="pA$sw0Rd", salt="s@lt")
    assert state_loaded.name == "different.json"
    loaded = state_loaded.load()
    assert all(v1 == v2 for v1, v2 in zip(loaded["list"], [1, 2, 3]))
    assert all(v1 == v2 for v1, v2 in zip(loaded["tuple"], (4, 5, 6)))
    assert loaded["dict"] == {"a": 1, "b": 2}
    assert loaded["str"] == "hello"
    assert loaded["int"] == 42
