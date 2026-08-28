"""A state read from a file on disk, and a state written to one.

That a payload of any format survives the trip through a file is checked in
`tests/test_state_contract.py`; what is here is the opening of the file itself.
"""

from pathlib import Path

import pytest

from iokit import FileState, Json, Yaml, file

DOCUMENT = {"hello": "world"}


@pytest.fixture(name="document")
def document_fixture(tmp_path: Path) -> Path:
    """A json document written to disk, to be read back as a state."""
    return Path(Json(DOCUMENT, "greeting").save(tmp_path).path)


def test_a_file_is_read_as_the_state_its_extension_names(document: Path) -> None:
    state = file(document)
    assert isinstance(state, FileState)
    assert state.name == "greeting.json"
    assert state.load() == DOCUMENT


def test_a_file_can_be_asked_for_as_the_format_it_is(document: Path) -> None:
    state = file(document, Json)
    assert isinstance(state, Json)
    assert state.load() == DOCUMENT


def test_a_file_of_another_format_than_the_one_asked_for_is_refused(document: Path) -> None:
    with pytest.raises(ValueError, match="Path must end with"):
        file(document, Yaml)


def test_a_state_read_from_a_file_is_pathed_by_it(document: Path) -> None:
    assert file(document).path == document.as_posix()


def test_a_missing_file_is_no_state(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        file(tmp_path / "missing.json")


def test_a_directory_is_no_state(tmp_path: Path) -> None:
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
