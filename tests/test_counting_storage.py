from pathlib import Path

import pytest

from iokit.storage import CountingStorage, MemoryStorage
from iokit.storage.local import StreamLocalStorage


def counted() -> CountingStorage[bytes]:
    """A counted memory storage, the tally starting empty."""
    return CountingStorage(MemoryStorage())


# the tally


def test_every_operation_is_counted() -> None:
    """Each operation of the storage protocol adds to the tally under its own name."""
    storage = counted()
    storage.push("data.json", b"{}")
    storage.pull("data.json")
    storage.exists("data.json")
    storage.size("data.json")
    list(storage.index())
    storage.remove("data.json")
    assert storage.calls == {
        "push": 1,
        "pull": 1,
        "exists": 1,
        "size": 1,
        "index": 1,
        "remove": 1,
    }


def test_repeated_calls_add_up() -> None:
    """Calling the same operation again raises its count rather than resetting it."""
    storage = counted()
    storage.push("data.json", b"{}")
    for _ in range(3):
        storage.pull("data.json")
    assert storage.calls["pull"] == 3


def test_operations_never_called_are_absent() -> None:
    """The tally holds only what has been called, never a zero."""
    storage = counted()
    assert storage.calls == {}
    storage.exists("data.json")
    assert storage.calls == {"exists": 1}


def test_failing_calls_are_counted_too() -> None:
    """A call is counted for having been made, whether it succeeds or raises."""
    storage = counted()
    with pytest.raises(FileNotFoundError):
        storage.pull("missing.json")
    assert storage.calls == {"pull": 1}


def test_index_counts_the_call_not_the_records() -> None:
    """Asking for an index counts once, however many records the walk goes on to yield."""
    storage = counted()
    storage.push("first.json", b"{}")
    storage.push("second.json", b"{}")
    storage.reset()
    records = storage.index()
    assert storage.calls == {"index": 1}
    assert sorted(records) == ["first.json", "second.json"]
    assert storage.calls == {"index": 1}


def test_the_tally_is_a_snapshot() -> None:
    """A tally read out once keeps its counts, later calls not reaching back into it."""
    storage = counted()
    storage.push("data.json", b"{}")
    snapshot = storage.calls
    storage.pull("data.json")
    storage.reset()
    assert snapshot == {"push": 1}


def test_reset_forgets_the_tally_only() -> None:
    """Resetting clears the counts and leaves the stored records untouched."""
    storage = counted()
    storage.push("data.json", b"{}")
    storage.reset()
    assert storage.calls == {}
    assert storage.pull("data.json") == b"{}"


# the backend underneath


def test_records_pass_through_untouched() -> None:
    """The wrapper stores nothing of its own, handing records to the backend it exposes."""
    backend = MemoryStorage()
    storage = CountingStorage(backend)
    storage.push("data.json", b"{}")
    assert backend.pull("data.json") == b"{}"
    assert storage.backend is backend


def test_the_backend_keeps_deciding_what_to_refuse() -> None:
    """The wrapper refuses nothing of its own, the backend answering for an existing record."""
    storage = counted()
    storage.push("data.json", b"{}")
    with pytest.raises(FileExistsError):
        storage.push("data.json", b"[]")
    storage.push("data.json", b"[]", force=True)
    assert storage.pull("data.json") == b"[]"


def test_index_is_filtered_by_prefix() -> None:
    """Only the records under the prefix are indexed, the wrapper adding no filtering of its own."""
    storage = counted()
    storage.push("reports/first.json", b"{}")
    storage.push("notes.txt", b"hello")
    assert list(storage.index(prefix="reports/")) == ["reports/first.json"]


def test_a_stream_storage_stays_a_stream_storage(tmp_path: Path) -> None:
    """Wrapping a stream storage keeps records streaming, handed on as the stream they are."""
    storage = CountingStorage(StreamLocalStorage(tmp_path))
    with (tmp_path / "source.json").open("wb") as source:
        source.write(b"{}")
    with (tmp_path / "source.json").open("rb") as source:
        storage.push("data.json", source)
    with storage.pull("data.json") as record:
        assert record.read() == b"{}"
    assert storage.calls == {"push": 1, "pull": 1}
