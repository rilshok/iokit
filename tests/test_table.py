"""What a dataframe is written as, over and above what every format owes in the contract."""

import pandas as pd
import pytest

from iokit import Csv, Pandas, Tsv

FRAME = pd.DataFrame(
    [
        {"name": "Alice", "age": 24},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 26},
    ],
)


@pytest.mark.parametrize(("kind", "separator"), [(Csv, b","), (Tsv, b"\t")])
def test_the_columns_are_parted_by_the_separator_of_the_format(
    kind: type[Pandas],
    separator: bytes,
) -> None:
    """One separator to a row, the header counted, and none of the other format's."""
    data = kind(FRAME, stem="table").data
    assert data.count(separator) == len(FRAME) + 1
    assert data.count(b"\t" if separator == b"," else b",") == 0


@pytest.mark.parametrize("kind", [Csv, Tsv])
def test_the_index_is_left_out_unless_it_is_asked_for(kind: type[Pandas]) -> None:
    """A frame is written without its index, which is a column of its own when asked for."""
    plain = kind(FRAME, stem="table")
    indexed = kind(FRAME, stem="table", index=True)
    assert indexed.size > plain.size
    assert list(indexed.load().columns) == ["Unnamed: 0", "name", "age"]
    assert plain.load().equals(indexed.load()[["name", "age"]])
