"""States that live outside memory: a file on disk, and an open buffer.

Where `save` is allowed to write and where it refuses to; what a payload survives is in
`tests/test_state_contract.py`.
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


def test_file_is_read_by_its_extension(document: Path) -> None:
    state = file(document)
    assert isinstance(state, FileState)
    assert state.name == "greeting.json"
    assert state.load() == DOCUMENT


def test_file_as_an_expected_format(document: Path) -> None:
    state = file(document, Json)
    assert isinstance(state, Json)
    assert state.load() == DOCUMENT


def test_file_of_another_format_refused(document: Path) -> None:
    with pytest.raises(ValueError, match="Path must end with"):
        file(document, Yaml)


def test_file_state_keeps_its_path(document: Path) -> None:
    assert file(document).path == document.as_posix()


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        file(tmp_path / "missing.json")


def test_directory_is_no_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not a regular file"):
        file(tmp_path)


def test_save_temp() -> None:
    """`save_temp` writes the state under its own name, and takes the file away afterwards."""
    state = Json(DOCUMENT, path="data/greeting.json")
    with state.save_temp() as temporary:
        path = Path(temporary.path)
        assert path.name == "greeting.json"
        assert temporary.size == state.size == path.stat().st_size
        assert temporary.load() == DOCUMENT
    assert not path.exists()


def test_timestamp_survives_a_file(tmp_path: Path) -> None:
    """When a state was last touched travels with it: onto the file, and back off it."""
    touched = Timestamp.from_datetime(datetime(2017, 1, 1, tzinfo=timezone.utc))
    state = Json(DOCUMENT, "greeting", timestamp=touched)
    assert state.timestamp.datetime == datetime(2017, 1, 1, tzinfo=timezone.utc)

    saved = state.save(tmp_path)
    assert Path(saved.path).stat().st_mtime == touched
    assert file(saved.path).timestamp == touched
    # a state made without one is stamped as it is made
    assert Json(DOCUMENT, "greeting").timestamp > touched.shift(timedelta(days=1))


def test_save_under_a_root(tmp_path: Path) -> None:
    """A path is relative to the root, and an absolute one lands under it all the same."""
    Json(DOCUMENT, path="reports/greeting.json").save(tmp_path)
    Json(DOCUMENT, path="/reports/absolute.json").save(tmp_path)
    assert (tmp_path / "reports/greeting.json").is_file()
    assert (tmp_path / "reports/absolute.json").is_file()


def test_save_outside_a_root_refused(tmp_path: Path) -> None:
    """A path leading out of the root is refused, so a state can never write over the way out."""
    with pytest.raises(ValueError, match="Path is outside of root"):
        Json(DOCUMENT, path="../escaped.json").save(tmp_path)
    assert not (tmp_path.parent / "escaped.json").exists()


def test_save_overwrites_only_when_forced(tmp_path: Path) -> None:
    state = Json(DOCUMENT, "greeting")
    state.save(tmp_path)
    with pytest.raises(FileExistsError, match="File already exists"):
        state.save(tmp_path)
    assert Json({"other": 1}, "greeting").save(tmp_path, force=True).load() == {"other": 1}


def test_save_makes_the_root(tmp_path: Path) -> None:
    """Saving into a root that is not there yet is an error unless the parents are asked for."""
    root = tmp_path / "missing/root"
    with pytest.raises(FileNotFoundError):
        Json(DOCUMENT, "greeting").save(root)
    assert Json(DOCUMENT, "greeting").save(root, parents=True).load() == DOCUMENT


def test_buffered_state_reads_its_buffer() -> None:
    """The state holds no copy: it measures and reads the buffer, which stays where it is."""
    state: BufferedState[str] = BufferedState(BytesIO(b"payload"), path="data.txt")
    assert state.size == len(b"payload")
    assert state.data == b"payload"
    assert state.load() == "payload"


def test_buffered_readers_are_independent() -> None:
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


def test_buffer_must_be_readable_and_seekable(tmp_path: Path) -> None:
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
