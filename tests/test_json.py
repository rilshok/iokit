from iokit.extensions.json import Json


def test_json_empty() -> None:
    state = Json({}, name="empty")
    assert state.name == "empty.json"
    assert state.size == 2
    assert state.data.getvalue() == b"{}"
    assert not state.load()


def test_json_single() -> None:
    state = Json({"key": "value"}, name="single")
    assert state.name == "single.json"
    assert state.data.getvalue() == b'{"key": "value"}'
    assert state.load() == {"key": "value"}


def test_json_multiple() -> None:
    state = Json({"first": 1, "second": 2}, name="multiple")
    assert state.name == "multiple.json"
    assert state.data.getvalue() == b'{"first": 1, "second": 2}'
    assert state.load() == {"first": 1, "second": 2}
    assert 20 < state.size < 30


def test_json_different() -> None:
    data = {
        "list": [1, 2, 3],
        "tuple": (4, 5, 6),
        "dict": {"a": 1, "b": 2},
        "str": "hello",
        "int": 42,
    }
    state = Json(data, name="different")
    assert state.name == "different.json"
    loaded = state.load()
    assert all(v1 == v2 for v1, v2 in zip(loaded["list"], [1, 2, 3]))
    assert all(v1 == v2 for v1, v2 in zip(loaded["tuple"], (4, 5, 6)))
    assert loaded["dict"] == {"a": 1, "b": 2}
    assert loaded["str"] == "hello"
    assert loaded["int"] == 42


def test_json_is_string() -> None:
    state = Json("hello", name="string")
    assert state.load() == "hello"
    assert state.size == 7
    assert state.data.getvalue() == b'"hello"'


def test_json_is_sequence() -> None:
    state = Json([1, 2, 3], name="sequence")
    assert state.load() == [1, 2, 3]
    assert state.size == 9
    assert state.data.getvalue() == b"[1, 2, 3]"
