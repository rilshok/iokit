from typing import Any

import pytest

from iokit import Yaml

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
        ([], b"[]\n"),
        ({"key": "value"}, b"key: value\n"),
        ({"first": 1, "second": 2}, b"first: 1\nsecond: 2\n"),
    ],
)
def test_a_value_is_written_as_yaml_and_read_back(value: object, data: bytes) -> None:
    state = Yaml(value, stem="document")
    assert state.data == data
    assert state.size == len(data)
    assert state.load() == value


def test_the_stem_names_the_state() -> None:
    assert Yaml([], stem="document").name == "document.yaml"


def test_what_yaml_has_no_shape_for_comes_back_as_what_it_has() -> None:
    """A tuple is written as a sequence, and a list is what is read back."""
    loaded = Yaml(DOCUMENT, stem="document").load()
    assert loaded == {**DOCUMENT, "tuple": [4, 5, 6]}
