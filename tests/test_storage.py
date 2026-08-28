from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from iokit.state import Json, Txt
from iokit.storage.local import (
    LocalStorage,
    MemoryStorage,
    StateStorage,
    StreamMemoryStorage,
)
from iokit.storage.storage import BinaryStorage

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


def test_memory_storage_roundtrip() -> None:
    storage = MemoryStorage()
    assert list(storage.index()) == []
    assert not storage.exists("data.bin")
    storage.push("data.bin", b"hello")
    assert storage.exists("data.bin")
    assert storage.pull("data.bin") == b"hello"
    assert storage.size("data.bin") == 5
    assert list(storage.index()) == ["data.bin"]
    storage.remove("data.bin")
    assert not storage.exists("data.bin")
    assert list(storage.index()) == []


def test_memory_storage_holds_an_empty_record() -> None:
    storage = MemoryStorage()
    storage.push("empty.bin", b"")
    assert storage.exists("empty.bin")
    assert storage.pull("empty.bin") == b""
    assert storage.size("empty.bin") == 0


def test_memory_storage_push_refuses_to_overwrite_without_force() -> None:
    storage = MemoryStorage()
    storage.push("data.bin", b"hello")
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.bin", b"other")
    assert storage.pull("data.bin") == b"hello"
    storage.push("data.bin", b"other", force=True)
    assert storage.pull("data.bin") == b"other"


def test_memory_storage_missing_record_raises() -> None:
    storage = MemoryStorage()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.size("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.remove("missing.bin")


def test_memory_storage_index_is_filtered_by_prefix() -> None:
    storage = MemoryStorage()
    storage.push("reports/first.bin", b"a")
    storage.push("reports/second.bin", b"b")
    storage.push("notes.bin", b"c")
    assert sorted(storage.index()) == ["notes.bin", "reports/first.bin", "reports/second.bin"]
    assert sorted(storage.index(prefix="reports/")) == [
        "reports/first.bin",
        "reports/second.bin",
    ]
    assert list(storage.index(prefix="nothing/")) == []


def test_memory_storage_index_is_a_snapshot() -> None:
    storage = MemoryStorage()
    storage.push("first.bin", b"a")
    storage.push("second.bin", b"b")
    seen: list[str] = []
    for uid in storage.index():
        seen.append(uid)
        storage.remove(uid)
        storage.push(f"{uid}.copy", b"c")
    assert sorted(seen) == ["first.bin", "second.bin"]
    assert sorted(storage.index()) == ["first.bin.copy", "second.bin.copy"]


def test_memory_storage_starts_empty_by_default() -> None:
    first = MemoryStorage()
    first.push("data.bin", b"hello")
    assert list(MemoryStorage().index()) == []


def test_memory_storage_serves_a_given_dictionary() -> None:
    records = {"data.bin": b"hello"}
    storage = MemoryStorage(records)
    assert storage.exists("data.bin")
    assert storage.pull("data.bin") == b"hello"
    assert list(storage.index()) == ["data.bin"]


def test_memory_storage_adopts_the_given_dictionary() -> None:
    records: dict[str, bytes] = {}
    storage = MemoryStorage(records)
    storage.push("data.bin", b"hello")
    assert records == {"data.bin": b"hello"}
    records["other.bin"] = b"world"
    assert storage.pull("other.bin") == b"world"
    storage.remove("data.bin")
    assert records == {"other.bin": b"world"}


def test_memory_storage_records_property_is_the_live_mapping() -> None:
    storage = MemoryStorage()
    storage.push("data.bin", b"hello")
    assert storage.records == {"data.bin": b"hello"}
    storage.records["other.bin"] = b"world"
    assert storage.pull("other.bin") == b"world"
    del storage.records["data.bin"]
    assert not storage.exists("data.bin")


def test_memory_storages_share_one_dictionary() -> None:
    records: dict[str, bytes] = {}
    first = MemoryStorage(records)
    second = MemoryStorage(records)
    first.push("data.bin", b"hello")
    assert second.pull("data.bin") == b"hello"
    second.remove("data.bin")
    assert not first.exists("data.bin")


def test_memory_storage_backs_a_state_storage() -> None:
    records: dict[str, bytes] = {}
    storage = StateStorage(MemoryStorage(records))
    storage.push("notes.txt", "hello")
    assert records == {"notes.txt": b"hello"}


def test_stream_memory_storage_roundtrip() -> None:
    storage = StreamMemoryStorage()
    storage.push("data.bin", BytesIO(b"hello"))
    assert storage.exists("data.bin")
    assert storage.size("data.bin") == 5
    with storage.pull("data.bin") as stream:
        assert stream.read() == b"hello"
    # every pull hands out its own reader over the record
    with storage.pull("data.bin") as stream:
        assert stream.read() == b"hello"


def test_stream_memory_storage_shares_the_backend() -> None:
    backend = MemoryStorage()
    storage = StreamMemoryStorage(backend)
    storage.push("data.bin", BytesIO(b"hello"))
    assert backend.pull("data.bin") == b"hello"
    backend.push("other.bin", b"world")
    with storage.pull("other.bin") as stream:
        assert stream.read() == b"world"


def test_stream_memory_storage_push_refuses_to_overwrite_without_force() -> None:
    storage = StreamMemoryStorage()
    storage.push("data.bin", BytesIO(b"hello"))
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.bin", BytesIO(b"other"))
    storage.push("data.bin", BytesIO(b"other"), force=True)
    with storage.pull("data.bin") as stream:
        assert stream.read() == b"other"


def test_stream_memory_storage_missing_record_raises() -> None:
    storage = StreamMemoryStorage()
    assert not storage.exists("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.size("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.remove("missing.bin")


def test_stream_memory_storage_index_is_filtered_by_prefix() -> None:
    storage = StreamMemoryStorage()
    storage.push("reports/first.bin", BytesIO(b"a"))
    storage.push("reports/second.bin", BytesIO(b"b"))
    storage.push("notes.bin", BytesIO(b"c"))
    assert sorted(storage.index()) == ["notes.bin", "reports/first.bin", "reports/second.bin"]
    assert sorted(storage.index(prefix="reports/")) == [
        "reports/first.bin",
        "reports/second.bin",
    ]


def test_stream_memory_storage_backs_a_binary_storage() -> None:
    storage = BinaryStorage(StreamMemoryStorage())
    storage.push("data.bin", b"hello")
    assert storage.pull("data.bin") == b"hello"
    assert storage.size("data.bin") == 5
    assert list(storage.index()) == ["data.bin"]
    storage.remove("data.bin")
    assert not storage.exists("data.bin")
