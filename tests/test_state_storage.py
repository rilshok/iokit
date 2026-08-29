"""Objects kept in a storage as states, the format taken from the extension of the uid.

The layers a storage adds go on the path the backend sees, never on the uid the caller uses.
"""

from pathlib import Path
from typing import Any

import pytest

from iokit import Json, LocalStorage, MemoryStorage, StateStorage, Txt

PASSWORD = "pA$sw0Rd"  # noqa: S105
SALT = "s@lt"
DOCUMENT: dict[str, Any] = {"list": [1, 2, 3], "str": "hello", "int": 42}


def test_payload_round_trip() -> None:
    backend = MemoryStorage()
    storage = StateStorage(backend)
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_format_follows_the_uid() -> None:
    """Nothing but the uid says how a payload is encoded, `.txt` making text of a string."""
    backend = MemoryStorage()
    storage = StateStorage(backend)
    storage.push("notes.txt", "hello")
    assert backend.pull("notes.txt") == b"hello"
    assert storage.pull("notes.txt") == "hello"


@pytest.mark.parametrize(
    ("config", "path"),
    [
        ({"compression": 9}, "data.json.gz"),
        ({"password": PASSWORD, "salt": SALT}, "data.json.enc"),
        ({"compression": True, "password": PASSWORD}, "data.json.gz.enc"),
    ],
    ids=["compressed", "encrypted", "compressed and encrypted"],
)
def test_layers_go_on_the_path_alone(
    config: dict[str, Any],
    path: str,
) -> None:
    """A configured layer shows in the path the backend holds, and in no uid of the storage."""
    backend = MemoryStorage()
    storage = StateStorage(backend, **config)
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == [path]
    assert list(storage.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_compression_shrinks_the_record() -> None:
    document = {"key": "value" * 1000}
    plain, packed = MemoryStorage(), MemoryStorage()
    StateStorage(plain).push("data.json", document)
    StateStorage(packed, compression=9).push("data.json", document)
    assert len(packed.pull("data.json.gz")) < len(plain.pull("data.json"))


def test_wrong_password() -> None:
    backend = MemoryStorage()
    StateStorage(backend, password=PASSWORD).push("data.json", DOCUMENT)
    with pytest.raises(ValueError, match="Decryption failed"):
        StateStorage(backend, password="wrong").pull("data.json")  # noqa: S106


def test_pull_state_is_pathed_by_its_uid() -> None:
    """The layers come off on the way out, so the state is the one that was pushed."""
    storage = StateStorage(MemoryStorage(), compression=1, password=PASSWORD)
    storage.push("data.json", DOCUMENT)
    state = storage.pull_state("data.json")
    assert state.path == "data.json"
    assert state.load() == DOCUMENT


def test_pull_state_as_an_expected_format() -> None:
    storage = StateStorage(MemoryStorage(), compression=1)
    storage.push("data.json", DOCUMENT)
    state = storage.pull_state("data.json", Json)
    assert isinstance(state, Json)
    assert state.load() == DOCUMENT
    with pytest.raises(ValueError, match="Path must end with"):
        storage.pull_state("data.json", Txt)


def test_push_overwrites_only_when_forced() -> None:
    storage = StateStorage(MemoryStorage(), compression=1)
    storage.push("data.json", DOCUMENT)
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.json", DOCUMENT)
    storage.push("data.json", {"other": 1}, force=True)
    assert storage.pull("data.json") == {"other": 1}


def test_exists_and_remove() -> None:
    storage = StateStorage(MemoryStorage(), compression=1)
    assert not storage.exists("data.json")
    storage.push("data.json", DOCUMENT)
    assert storage.exists("data.json")
    storage.remove("data.json")
    assert not storage.exists("data.json")


def test_size_is_the_stored_size() -> None:
    """The layers are part of the record, so what is measured is the stored bytes."""
    backend = MemoryStorage()
    storage = StateStorage(backend, compression=9)
    storage.push("data.json", DOCUMENT)
    assert storage.size("data.json") == len(backend.pull("data.json.gz"))


@pytest.mark.parametrize(
    "storage",
    [
        StateStorage(MemoryStorage()),
        StateStorage(MemoryStorage(), compression=1),
        StateStorage(MemoryStorage(), password=PASSWORD),
    ],
    ids=["plain", "compressed", "encrypted"],
)
def test_missing_record(storage: StateStorage) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull_state("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.remove("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.size("missing.json")


def test_index_is_filtered_by_prefix() -> None:
    storage = StateStorage(MemoryStorage(), compression=1)
    storage.push("reports/first.json", DOCUMENT)
    storage.push("reports/second.json", DOCUMENT)
    storage.push("notes.txt", "hello")
    assert sorted(storage.index()) == ["notes.txt", "reports/first.json", "reports/second.json"]
    assert sorted(storage.index(prefix="reports/")) == [
        "reports/first.json",
        "reports/second.json",
    ]


def test_over_a_local_storage(tmp_path: Path) -> None:
    """A local storage underneath holds the layered path as a file, and reads it back."""
    storage = StateStorage(LocalStorage(tmp_path), compression=9, password=PASSWORD)
    storage.push("nested/dir/data.json", DOCUMENT)
    assert (tmp_path / "nested/dir/data.json.gz.enc").is_file()
    assert list(storage.index()) == ["nested/dir/data.json"]
    assert storage.pull("nested/dir/data.json") == DOCUMENT
    storage.remove("nested/dir/data.json")
    assert not storage.exists("nested/dir/data.json")
