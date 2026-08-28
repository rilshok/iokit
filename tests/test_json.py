from typing import Any

import pytest

from iokit import Json

DOCUMENT: dict[str, Any] = {
    "list": [1, 2, 3],
    "tuple": (4, 5, 6),
    "dict": {"a": 1, "b": 2},
    "str": "hello",
    "int": 42,
}


@pytest.mark.parametrize(
    ("value", "data"),
    [
        ({}, b"{}"),
        ({"key": "value"}, b'{"key": "value"}'),
        ({"first": 1, "second": 2}, b'{"first": 1, "second": 2}'),
        ("hello", b'"hello"'),
        ([1, 2, 3], b"[1, 2, 3]"),
    ],
)
def test_a_value_is_written_as_json_and_read_back(value: object, data: bytes) -> None:
    state = Json(value, stem="document")
    assert state.data == data
    assert state.size == len(data)
    assert state.load() == value


def test_the_stem_names_the_state() -> None:
    assert Json({}, stem="document").name == "document.json"


def test_what_json_has_no_shape_for_comes_back_as_what_it_has() -> None:
    """A tuple is written as an array, and an array is what is read back."""
    loaded = Json(DOCUMENT, stem="document").load()
    assert loaded == {**DOCUMENT, "tuple": [4, 5, 6]}
