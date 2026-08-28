"""A state read from a file on disk, and a state written to one.

That a payload of any format survives the trip through a file is checked in
`tests/test_state_contract.py`; what is here is the opening of the file itself.
"""

from pathlib import Path

import pytest

from iokit import Json, Yaml, file
from iokit.state import FileState

DOCUMENT = {"hello": "world"}


@pytest.fixture
def document(tmp_path: Path) -> Path:
    return Path(Json(DOCUMENT, "greeting").save(tmp_path).path)


def test_file_untyped(document: Path) -> None:
    state = file(document)
    assert isinstance(state, FileState)
    assert state.name == "greeting.json"
    assert state.load() == DOCUMENT


def test_file_expected_type(document: Path) -> None:
    state = file(document, Json)
    assert isinstance(state, Json)
    assert state.name == "greeting.json"
    assert state.load() == DOCUMENT


def test_file_unexpected_type(document: Path) -> None:
    with pytest.raises(ValueError, match="Path must end with"):
        file(document, Yaml)


def test_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        file(tmp_path / "missing.json")


def test_file_keeps_path(document: Path) -> None:
    assert file(document).path == document.as_posix()


def test_file_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not a regular file"):
        file(tmp_path)


def test_a_temporary_file_holds_the_state_until_the_context_is_left() -> None:
    """`save_temp` writes the state under its own name, and takes the file away afterwards."""
    state = Json(DOCUMENT, path="data/greeting.json")
    with state.save_temp() as temporary:
        path = Path(temporary.path)
        assert path.name == "greeting.json"
        assert temporary.size == state.size == path.stat().st_size
        assert temporary.load() == DOCUMENT
    assert not path.exists()
