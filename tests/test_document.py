"""The text the document formats put on the wire, over and above `tests/test_state_contract.py`."""

from typing import Any

import pytest

from iokit import Json, Jsonl, LoadedState, Yaml, Yml

DOCUMENT: dict[str, Any] = {
    "list": [1, 2, 3],
    "tuple": (4, 5, 6),
    "dict": {"a": 1, "b": 2},
    "str": "hello",
    "int": 42,
}


@pytest.mark.parametrize(
    ("kind", "value", "data"),
    [
        (Json, {}, b"{}"),
        (Json, {"key": "value"}, b'{"key": "value"}'),
        (Json, {"first": 1, "second": 2}, b'{"first": 1, "second": 2}'),
        (Json, "hello", b'"hello"'),
        (Json, [1, 2, 3], b"[1, 2, 3]"),
        (Yaml, [], b"[]\n"),
        (Yaml, {"key": "value"}, b"key: value\n"),
        (Yaml, {"first": 1, "second": 2}, b"first: 1\nsecond: 2\n"),
        (Yml, {"key": "value"}, b"key: value\n"),
        (Jsonl, [], b""),
        (Jsonl, [{"key": "value"}], b'{"key":"value"}\n'),
        (Jsonl, [{"key": "value"}] * 2, b'{"key":"value"}\n{"key":"value"}\n'),
    ],
)
def test_value_is_written_as_spelled(
    kind: type[Json | Yaml | Jsonl],
    value: object,
    data: bytes,
) -> None:
    state = kind(value, stem="document")
    assert state.data == data
    assert state.load() == value


@pytest.mark.parametrize("kind", [Json, Yaml, Yml])
def test_tuple_comes_back_a_list(
    kind: type[Json | Yaml],
) -> None:
    """A tuple is written as a sequence, and a sequence is what is read back."""
    loaded = kind(DOCUMENT, stem="document").load()
    assert loaded == {**DOCUMENT, "tuple": [4, 5, 6]}


def test_lines_keep_their_own_shape() -> None:
    """The records of a jsonl need no shape in common, each line standing on its own."""
    lines = [{"a": number, "bb": number**2, "ccc": number**3} for number in range(10)]
    assert Jsonl(lines, stem="document").load() == lines


@pytest.mark.parametrize(
    ("value", "data"),
    [(42, b"42"), (3.14, b"3.14"), (True, b"true"), (None, b"null")],
)
def test_json_scalar(value: object, data: bytes) -> None:
    """Whatever a json file can hold, a `Json` state holds as well."""
    state = Json(value, stem="scalar")
    assert state.data == data
    assert state.load() == value
    assert Json.from_state(LoadedState(data, path="scalar.json")).load() == value
    assert LoadedState(data, path="scalar.json").load() == value
