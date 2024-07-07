from iokit.extensions.yaml import Yaml


def test_yaml_empty() -> None:
    state = Yaml([], name="empty")
    assert state.name == "empty.yaml"
    assert state.size == 3
    assert state.data.getvalue() == b"[]\n"
    assert not state.load()


def test_yaml_single() -> None:
    state = Yaml({"key": "value"}, name="single")
    assert state.name == "single.yaml"
    assert state.load() == {"key": "value"}


def test_yaml_multiple() -> None:
    state = Yaml({"first": 1, "second": 2}, name="multiple")
    assert state.name == "multiple.yaml"
    assert state.load() == {"first": 1, "second": 2}
    assert state.size == 19


def test_yaml_different() -> None:
    data = {
        "list": [1, 2, 3],
        "tuple": (4, 5, 6),
        "dict": {"a": 1, "b": 2},
        "str": "hello",
        "int": 42,
    }
    state = Yaml(data, name="different")
    assert state.name == "different.yaml"
    loaded = state.load()
    assert all(v1 == v2 for v1, v2 in zip(loaded["list"], [1, 2, 3]))
    assert all(v1 == v2 for v1, v2 in zip(loaded["tuple"], (4, 5, 6)))
    assert loaded["dict"] == {"a": 1, "b": 2}
    assert loaded["str"] == "hello"
    assert loaded["int"] == 42
