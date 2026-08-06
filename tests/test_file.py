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
