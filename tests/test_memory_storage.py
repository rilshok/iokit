"""Records kept in a dictionary, and the streams served out of one.

What every byte storage owes a caller is checked in `tests/test_storage_contract.py`, over a
memory storage among the others. What is here is the dictionary itself: whose it is, what it
is allowed to hold, and what the storage makes of a key it could never hand a record back
under.
"""

from io import BytesIO

import pytest

from iokit import MemoryStorage, StreamMemoryStorage


def test_a_storage_of_its_own_starts_empty() -> None:
    """Each storage keeps its own records, nothing being shared behind the class."""
    MemoryStorage().push("data.bin", b"hello")
    assert list(MemoryStorage().index()) == []


def test_the_given_dictionary_is_the_storage() -> None:
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


def test_the_records_of_a_storage_are_the_live_mapping() -> None:
    storage = MemoryStorage()
    storage.push("data.bin", b"hello")
    assert storage.records == {"data.bin": b"hello"}
    storage.records["other.bin"] = b"world"
    assert storage.pull("other.bin") == b"world"
    del storage.records["data.bin"]
    assert not storage.exists("data.bin")


def test_two_storages_over_one_dictionary_hold_the_same_records() -> None:
    records: dict[str, bytes] = {}
    first, second = MemoryStorage(records), MemoryStorage(records)
    first.push("data.bin", b"hello")
    assert second.pull("data.bin") == b"hello"
    second.remove("data.bin")
    assert not first.exists("data.bin")


@pytest.mark.parametrize("key", ["", ".", "..", "./data.bin", "data.bin/", "a//b.bin"])
def test_a_key_that_names_no_record_is_left_where_it_lies(key: str) -> None:
    """A mapping may hold whatever it likes; what is no uid is simply not a record."""
    records = {key: b"hello", "data.bin": b"world"}
    storage = MemoryStorage(records)
    assert list(storage.index()) == ["data.bin"]
    with pytest.raises(ValueError, match="is not a relative path naming a record"):
        storage.pull(key)
    assert records[key] == b"hello"


def test_the_index_yields_only_what_the_storage_can_hand_back() -> None:
    records = {"": b"a", "./data.bin": b"b", "reports/first.bin": b"c"}
    storage = MemoryStorage(records)
    for uid in storage.index():
        assert storage.exists(uid)
        assert storage.pull(uid) == records[uid]


def test_a_stream_storage_hands_out_a_reader_of_its_own_on_every_pull() -> None:
    """The record stays where it is, so reading one stream leaves the other whole."""
    storage = StreamMemoryStorage()
    storage.push("data.bin", BytesIO(b"hello"))
    first, second = storage.pull("data.bin"), storage.pull("data.bin")
    with first, second:
        assert first.read(2) == b"he"
        assert second.read() == b"hello"


def test_a_stream_storage_keeps_its_records_in_the_backend_it_is_given() -> None:
    """Streams and bytes are two views of one dictionary of records."""
    backend = MemoryStorage()
    storage = StreamMemoryStorage(backend)
    storage.push("data.bin", BytesIO(b"hello"))
    assert backend.pull("data.bin") == b"hello"
    backend.push("other.bin", b"world")
    with storage.pull("other.bin") as record:
        assert record.read() == b"world"
