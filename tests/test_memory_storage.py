"""Records kept in a dictionary: whose it is, and what it is allowed to hold.

The contract every storage keeps is in `tests/test_storage_contract.py`.
"""

from io import BytesIO

import pytest

from iokit import MemoryStorage, StreamMemoryStorage


def test_each_storage_starts_empty() -> None:
    """Each storage keeps its own records, nothing being shared behind the class."""
    MemoryStorage().push("data.bin", b"hello")
    assert list(MemoryStorage().index()) == []


def test_given_dictionary_is_adopted() -> None:
    """A mapping handed in is adopted, not copied, so the two sides see each other's writes."""
    records = {"data.bin": b"hello"}
    storage = MemoryStorage(records)
    assert list(storage.index()) == ["data.bin"]
    assert storage.pull("data.bin") == b"hello"
    storage.push("other.bin", b"world")
    assert records == {"data.bin": b"hello", "other.bin": b"world"}
    records["third.bin"] = b"!"
    assert storage.pull("third.bin") == b"!"
    storage.remove("data.bin")
    assert sorted(records) == ["other.bin", "third.bin"]


def test_records_are_the_live_mapping() -> None:
    storage = MemoryStorage()
    storage.push("data.bin", b"hello")
    assert storage.records == {"data.bin": b"hello"}
    storage.records["other.bin"] = b"world"
    assert storage.pull("other.bin") == b"world"
    del storage.records["data.bin"]
    assert not storage.exists("data.bin")


def test_two_storages_one_dictionary() -> None:
    records: dict[str, bytes] = {}
    first, second = MemoryStorage(records), MemoryStorage(records)
    first.push("data.bin", b"hello")
    assert second.pull("data.bin") == b"hello"
    second.remove("data.bin")
    assert not first.exists("data.bin")


@pytest.mark.parametrize("key", ["", ".", "..", "./data.bin", "data.bin/", "a//b.bin"])
def test_key_that_names_no_record(key: str) -> None:
    """A mapping may hold whatever it likes; what is no uid is simply not a record."""
    records = {key: b"hello", "data.bin": b"world"}
    storage = MemoryStorage(records)
    assert list(storage.index()) == ["data.bin"]
    with pytest.raises(ValueError, match="is not a relative path naming a record"):
        storage.pull(key)
    assert records[key] == b"hello"


def test_index_yields_only_records() -> None:
    records = {"": b"a", "./data.bin": b"b", "reports/first.bin": b"c"}
    storage = MemoryStorage(records)
    for uid in storage.index():
        assert storage.exists(uid)
        assert storage.pull(uid) == records[uid]


def test_stream_readers_are_independent() -> None:
    """The record stays where it is, so reading one stream leaves the other whole."""
    storage = StreamMemoryStorage()
    storage.push("data.bin", BytesIO(b"hello"))
    first, second = storage.pull("data.bin"), storage.pull("data.bin")
    with first, second:
        assert first.read(2) == b"he"
        assert second.read() == b"hello"


def test_stream_shares_its_backend() -> None:
    """Streams and bytes are two views of one dictionary of records."""
    backend = MemoryStorage()
    storage = StreamMemoryStorage(backend)
    storage.push("data.bin", BytesIO(b"hello"))
    assert backend.pull("data.bin") == b"hello"
    backend.push("other.bin", b"world")
    with storage.pull("other.bin") as record:
        assert record.read() == b"world"
