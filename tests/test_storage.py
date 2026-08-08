from pathlib import Path
from typing import Any

import pytest

from iokit.state import Json, Txt
from iokit.storage.local import LocalStorage, MemoryStorage, StateStorage

DOCUMENT: dict[str, Any] = {"list": [1, 2, 3], "str": "hello", "int": 42}


def state_storage(**config: object) -> tuple[MemoryStorage, StateStorage]:
    backend = MemoryStorage()
    return backend, StateStorage(backend, **config)  # type: ignore[arg-type]


def test_plain_roundtrip() -> None:
    backend, storage = state_storage()
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_compressed_roundtrip() -> None:
    backend, storage = state_storage(compression=9)
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == ["data.json.gz"]
    assert list(storage.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_encrypted_roundtrip() -> None:
    backend, storage = state_storage(password="pA$sw0Rd", salt="s@lt")
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == ["data.json.enc"]
    assert list(storage.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_compressed_and_encrypted_roundtrip() -> None:
    backend, storage = state_storage(compression=True, password="pA$sw0Rd")
    storage.push("data.json", DOCUMENT)
    assert list(backend.index()) == ["data.json.gz.enc"]
    assert list(storage.index()) == ["data.json"]
    assert storage.pull("data.json") == DOCUMENT


def test_compression_shrinks_the_record() -> None:
    document = {"key": "value" * 1000}
    plain_backend, plain = state_storage()
    packed_backend, packed = state_storage(compression=9)
    plain.push("data.json", document)
    packed.push("data.json", document)
    assert len(packed_backend.pull("data.json.gz")) < len(plain_backend.pull("data.json"))


def test_wrong_password_is_rejected() -> None:
    backend, storage = state_storage(password="pA$sw0Rd")
    storage.push("data.json", DOCUMENT)
    with pytest.raises(ValueError, match="Decryption failed"):
        StateStorage(backend, password="wrong").pull("data.json")


def test_format_follows_the_uid_extension() -> None:
    backend, storage = state_storage()
    storage.push("notes.txt", "hello")
    assert backend.pull("notes.txt") == b"hello"
    assert storage.pull("notes.txt") == "hello"


def test_pull_state_keeps_the_uid_as_path() -> None:
    _, storage = state_storage(compression=1, password="pA$sw0Rd")
    storage.push("data.json", DOCUMENT)
    state = storage.pull_state("data.json")
    assert state.path == "data.json"
    assert state.load() == DOCUMENT


def test_pull_state_checks_the_expected_type() -> None:
    _, storage = state_storage(compression=1)
    storage.push("data.json", DOCUMENT)
    state = storage.pull_state("data.json", Json)
    assert isinstance(state, Json)
    assert state.load() == DOCUMENT
    with pytest.raises(ValueError, match="Path must end with"):
        storage.pull_state("data.json", Txt)


def test_push_refuses_to_overwrite_without_force() -> None:
    _, storage = state_storage(compression=1)
    storage.push("data.json", DOCUMENT)
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.json", DOCUMENT)
    storage.push("data.json", {"other": 1}, force=True)
    assert storage.pull("data.json") == {"other": 1}


def test_exists_and_remove() -> None:
    _, storage = state_storage(compression=1, password="pA$sw0Rd")
    assert not storage.exists("data.json")
    storage.push("data.json", DOCUMENT)
    assert storage.exists("data.json")
    storage.remove("data.json")
    assert not storage.exists("data.json")


def test_size_is_the_stored_size(tmp_path: Path) -> None:
    for backend in (MemoryStorage(), LocalStorage(tmp_path)):
        backend.push("data.json", b'{"key": 1}')
        assert backend.size("data.json") == len(b'{"key": 1}')

    backend, storage = state_storage(compression=9, password="pA$sw0Rd")
    storage.push("data.json", DOCUMENT)
    assert storage.size("data.json") == len(backend.pull("data.json.gz.enc"))


@pytest.mark.parametrize("config", [{}, {"compression": 1}, {"password": "pA$sw0Rd"}])
def test_missing_record_raises(config: dict[str, Any]) -> None:
    _, storage = state_storage(**config)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull_state("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.remove("missing.json")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.size("missing.json")


def test_index_is_filtered_by_prefix() -> None:
    _, storage = state_storage(compression=1)
    storage.push("reports/first.json", DOCUMENT)
    storage.push("reports/second.json", DOCUMENT)
    storage.push("notes.txt", "hello")
    assert sorted(storage.index()) == ["notes.txt", "reports/first.json", "reports/second.json"]
    assert sorted(storage.index(prefix="reports/")) == [
        "reports/first.json",
        "reports/second.json",
    ]


def test_local_backend_roundtrip(tmp_path: Path) -> None:
    storage = StateStorage(LocalStorage(tmp_path), compression=9, password="pA$sw0Rd")
    storage.push("nested/dir/data.json", DOCUMENT)
    assert (tmp_path / "nested/dir/data.json.gz.enc").is_file()
    assert list(storage.index()) == ["nested/dir/data.json"]
    assert storage.pull("nested/dir/data.json") == DOCUMENT
    storage.remove("nested/dir/data.json")
    assert not storage.exists("nested/dir/data.json")


def test_local_backend_stays_under_its_root(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "root")
    with pytest.raises(ValueError, match="outside of the storage root"):
        storage.push("../escaped.json", b"{}")
