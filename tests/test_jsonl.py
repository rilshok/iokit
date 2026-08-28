import pytest

from iokit import Jsonl


@pytest.mark.parametrize(
    ("lines", "data"),
    [
        ([], b""),
        ([{"key": "value"}], b'{"key":"value"}\n'),
        ([{"key": "value"}] * 2, b'{"key":"value"}\n{"key":"value"}\n'),
    ],
)
def test_lines_are_written_one_per_line_and_read_back(
    lines: list[dict[str, str]],
    data: bytes,
) -> None:
    state = Jsonl(lines, stem="document")
    assert state.data == data
    assert state.size == len(data)
    assert state.load() == lines


def test_the_stem_names_the_state() -> None:
    assert Jsonl([], stem="document").name == "document.jsonl"


def test_lines_of_their_own_shape_each_keep_it() -> None:
    lines = [{"a": number, "bb": number**2, "ccc": number**3} for number in range(10)]
    assert Jsonl(lines, stem="document").load() == lines
