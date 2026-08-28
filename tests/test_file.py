"""States that live outside memory: a file on disk, and an open buffer.

That a payload of any format survives the trip through a file is checked in
`tests/test_state_contract.py`. What is here is the file itself - where `save` is allowed to
write and where it refuses to - and a state that reads its bytes from a buffer as they are
asked for rather than holding them.
"""

import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest

from iokit import BufferedState, FileState, Json, Yaml, file
from iokit.utils.time import Timestamp

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


def test_a_state_and_its_file_keep_the_same_timestamp(tmp_path: Path) -> None:
    """When a state was last touched travels with it: onto the file, and back off it."""
    touched = Timestamp.from_datetime(datetime(2017, 1, 1, tzinfo=timezone.utc))
    state = Json(DOCUMENT, "greeting", timestamp=touched)
    assert state.timestamp.datetime == datetime(2017, 1, 1, tzinfo=timezone.utc)

    saved = state.save(tmp_path)
    assert Path(saved.path).stat().st_mtime == touched
    assert file(saved.path).timestamp == touched
    # a state made without one is stamped as it is made
    assert Json(DOCUMENT, "greeting").timestamp > touched.shift(timedelta(days=1))


def test_a_state_is_saved_under_the_root_it_is_given(tmp_path: Path) -> None:
    """A path is relative to the root, and an absolute one lands under it all the same."""
    Json(DOCUMENT, path="reports/greeting.json").save(tmp_path)
    Json(DOCUMENT, path="/reports/absolute.json").save(tmp_path)
    assert (tmp_path / "reports/greeting.json").is_file()
    assert (tmp_path / "reports/absolute.json").is_file()


def test_a_state_is_not_saved_outside_of_its_root(tmp_path: Path) -> None:
    """A path leading out of the root is refused, so a state can never write over the way out."""
    with pytest.raises(ValueError, match="Path is outside of root"):
        Json(DOCUMENT, path="../escaped.json").save(tmp_path)
    assert not (tmp_path.parent / "escaped.json").exists()


def test_a_saved_state_is_overwritten_only_when_it_is_forced(tmp_path: Path) -> None:
    state = Json(DOCUMENT, "greeting")
    state.save(tmp_path)
    with pytest.raises(FileExistsError, match="File already exists"):
        state.save(tmp_path)
    assert Json({"other": 1}, "greeting").save(tmp_path, force=True).load() == {"other": 1}


def test_a_root_is_made_along_with_its_parents_when_it_is_asked_for(tmp_path: Path) -> None:
    """Saving into a root that is not there yet is an error unless the parents are asked for."""
    root = tmp_path / "missing/root"
    with pytest.raises(FileNotFoundError):
        Json(DOCUMENT, "greeting").save(root)
    assert Json(DOCUMENT, "greeting").save(root, parents=True).load() == DOCUMENT


def test_a_buffered_state_reads_its_bytes_from_the_buffer_it_is_given() -> None:
    """The state holds no copy: it measures and reads the buffer, which stays where it is."""
    state: BufferedState[str] = BufferedState(BytesIO(b"payload"), path="data.txt")
    assert state.size == len(b"payload")
    assert state.data == b"payload"
    assert state.load() == "payload"


def test_a_buffered_state_hands_out_a_reader_of_its_own_every_time() -> None:
    """Each reader has a cursor of its own, so reading one leaves the others where they were."""
    state: BufferedState[bytes] = BufferedState(BytesIO(b"payload"), path="data.dat")
    with state.buffer as first, state.buffer as second:
        assert first.read(3) == b"pay"
        assert second.read() == b"payload"
        assert first.read() == b"load"
        assert second.seek(0) == 0
        assert second.read(3) == b"pay"
    # closing the readers spares the buffer underneath, which the state still reads from
    assert state.data == b"payload"


def test_a_buffer_that_cannot_be_read_over_is_no_state(tmp_path: Path) -> None:
    """A state reads its buffer more than once and from anywhere, so it needs both of those."""
    with (
        (tmp_path / "out.txt").open("wb") as write_only,
        pytest.raises(ValueError, match="readable"),
    ):
        BufferedState(write_only, path="data.txt")

    read_end, write_end = os.pipe()
    os.close(write_end)
    with os.fdopen(read_end, "rb") as pipe, pytest.raises(ValueError, match="seekable"):
        BufferedState(pipe, path="data.txt")
