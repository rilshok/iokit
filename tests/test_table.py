import pandas as pd

from iokit import Csv, Tsv


def _test_teble_data() -> list[dict[str, str | int]]:
    return [
        {"name": "Alice", "age": 24},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 26},
    ]


def test_csv() -> None:
    frame = pd.DataFrame(_test_teble_data())
    state = Csv(frame, name="test")
    assert str(state.name) == "test.csv"
    assert frame.equals(state.load())
    assert Csv(frame, index=True).size > state.size
    assert state.load().equals(Csv(frame, index=True).load()[["name", "age"]])
    assert len([1 for ch in state.data if ch == b","[0]]) == 4


def test_tsv() -> None:
    frame = pd.DataFrame(_test_teble_data())
    state = Tsv(frame, name="test")
    assert str(state.name) == "test.tsv"
    assert frame.equals(state.load())
    assert Tsv(frame, index=True).size > state.size
    assert state.load().equals(Tsv(frame, index=True).load()[["name", "age"]])
    assert len([1 for ch in state.data if ch == b"\t"[0]]) == 4
