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
    assert frame.equals(Csv(frame).load())
    assert Csv(frame, index=True).size > Csv(frame).size
    assert Csv(frame).load().equals(Csv(frame, index=True).load()[["name", "age"]])
    assert len([1 for ch in Csv(frame).data if ch == b","[0]]) == 4


def test_tsv() -> None:
    frame = pd.DataFrame(_test_teble_data())
    assert frame.equals(Tsv(frame).load())
    assert Tsv(frame, index=True).size > Tsv(frame).size
    assert Tsv(frame).load().equals(Tsv(frame, index=True).load()[["name", "age"]])
    assert len([1 for ch in Tsv(frame).data if ch == b"\t"[0]]) == 4
