from iokit import Jsonl


def test_jsonl_empty() -> None:
    state = Jsonl([], name="empty")
    assert state.name == "empty.jsonl"
    assert state.size == 0
    assert state.data.getvalue() == b""
    assert not state.load()


def test_jsonl_single() -> None:
    state = Jsonl([{"key": "value"}], name="single")
    assert state.name == "single.jsonl"
    assert state.data.getvalue() == b'{"key":"value"}\n'
    assert state.load() == [{"key": "value"}]


def test_jsonl_multiple_repeat() -> None:
    state = Jsonl([{"key": "value"}] * 2, name="multiple")
    assert state.name == "multiple.jsonl"
    assert state.data.getvalue() == b'{"key":"value"}\n{"key":"value"}\n'
    assert state.load() == [{"key": "value"}] * 2


def test_jsonl_multiple_similar() -> None:
    data = [{"a": i, "bb": i**2, "ccc": i**3} for i in range(10)]
    state = Jsonl(data, name="multiple")
    assert state.name == "multiple.jsonl"
    assert state.load() == data
