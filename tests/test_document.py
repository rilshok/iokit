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


def test_bare_number_is_no_document() -> None:
    """A json file may hold a bare number; a `Json` state is a document, and says so."""
    number: Json = Json.from_state(LoadedState(b"42", path="number.json"))
    assert number.data == b"42"
    with pytest.raises(TypeError, match="Expected loaded data of type"):
        number.load()
    # read without the promise of a format, the same bytes come back as the number they are
    assert LoadedState(b"42", path="number.json").load() == 42
