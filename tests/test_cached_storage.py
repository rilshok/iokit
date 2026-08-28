from pathlib import Path

import pytest

from iokit.storage import CachedStorage, CountingStorage, LocalStorage, MemoryStorage, Storage
from iokit.storage.local import StreamLocalStorage

Counted = CountingStorage[bytes]


def cached() -> tuple[Counted, Counted, CachedStorage[bytes]]:
    """A cache over two counted memory storages, to tell which side answered a call."""
    hot: Counted = CountingStorage(MemoryStorage())
    cold: Counted = CountingStorage(MemoryStorage())
    return hot, cold, CachedStorage(hot, cold)


def quiet(*storages: Counted) -> None:
    """Forget the traffic of the arrangement, so that a test counts only what it acts on."""
    for storage in storages:
        storage.reset()


def stored(storage: Counted, uid: str) -> bytes | None:
    """Read a record straight from the counted storage, without counting the lookup.

    Only for byte storages: on a stream storage this would consume the record.
    """
    backend = storage.backend
    return backend.pull(uid) if backend.exists(uid) else None


def refuse(uid: str, record: bytes, *, force: bool = False) -> None:  # noqa: ARG001
    """Stand in for the push of a cold storage that is down."""
    msg = "cold storage is down"
    raise RuntimeError(msg)


# pushing


def test_push_reaches_both_storages() -> None:
    """A pushed record lands in the cache and in the cold storage alike."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    assert stored(hot, "data.json") == b"{}"
    assert stored(cold, "data.json") == b"{}"


def test_push_writes_to_the_cold_storage_once() -> None:
    """Pushing costs the cold storage one existence lookup and one write, no more."""
    _, cold, storage = cached()
    storage.push("data.json", b"{}")
    assert cold.calls == {"exists": 1, "push": 1}


def test_a_forced_push_skips_the_existence_lookup() -> None:
    """A forced push goes straight to writing, asking the cold storage nothing beforehand."""
    _, cold, storage = cached()
    storage.push("data.json", b"{}", force=True)
    assert cold.calls == {"push": 1}


def test_push_refuses_to_overwrite_without_force() -> None:
    """An unforced push over an existing record refuses before writing anything anywhere."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.json", b"[]")
    # the refusal comes before anything is written, on either side
    assert cold.calls == {"exists": 1}
    assert stored(cold, "data.json") == b"{}"
    assert stored(hot, "data.json") is None


def test_a_forced_push_overwrites_both_storages() -> None:
    """A forced push replaces the record on both sides, leaving no stale copy cached."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    storage.push("data.json", b"[]", force=True)
    assert stored(hot, "data.json") == b"[]"
    assert stored(cold, "data.json") == b"[]"


# pulling


def test_pull_warms_the_cache_from_the_cold_storage() -> None:
    """A record missing from the cache is read from the cold storage and cached on the way out."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert stored(hot, "data.json") == b"{}"
    # the cold storage is read once, and never asked whether the record is there
    assert cold.calls == {"pull": 1}


def test_a_warmed_record_is_pulled_from_the_cache_alone() -> None:
    """Once warmed, a record is served without the cold storage hearing about it."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    assert storage.pull("data.json") == b"{}"
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "pull": 1}


def test_a_pushed_record_is_pulled_from_the_cache_alone() -> None:
    """Pushing warms the cache too, so reading a record back never reaches the cold storage."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert cold.calls == {}


def test_pull_of_a_missing_record_caches_nothing() -> None:
    """A read that finds nothing leaves the cache as empty as it was."""
    hot, cold, storage = cached()
    with pytest.raises(FileNotFoundError):
        storage.pull("missing.json")
    assert stored(hot, "missing.json") is None
    assert cold.calls == {"pull": 1}
    assert hot.calls == {"exists": 1}


def test_a_record_dropped_from_the_cache_is_warmed_back() -> None:
    """Evicting the cached copy behind the cache's back costs a read, never the record."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    hot.backend.remove("data.json")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert stored(hot, "data.json") == b"{}"
    assert cold.calls == {"pull": 1}


# asking after a record


def test_exists_is_answered_by_the_cache_alone() -> None:
    """A cached record is known to exist without asking the cold storage."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.exists("data.json")
    assert cold.calls == {}
    assert hot.calls == {"exists": 1}


def test_exists_falls_back_to_the_cold_storage() -> None:
    """What the cache has never seen is looked up in the cold storage, present or not."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.exists("data.json")
    assert not storage.exists("missing.json")
    assert cold.calls == {"exists": 2}
    assert hot.calls == {"exists": 2}


def test_size_is_answered_by_the_cache_alone() -> None:
    """The size of a cached record is measured on the cache, the two copies being alike.

    The cache holds the record as the cold storage gave it, so measuring either is the same;
    what a cache holding something else reports is pinned down further below.
    """
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.size("data.json") == len(b"{}")
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "size": 1}


def test_size_falls_back_to_the_cold_storage_in_a_single_lookup() -> None:
    """Sizing an uncached record asks the cold storage once and does not pull it into the cache."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.size("data.json") == len(b"{}")
    # the record is not cached on the way, and the cold storage is asked for the size only
    assert stored(hot, "data.json") is None
    assert cold.calls == {"size": 1}
    assert hot.calls == {"exists": 1}


# walking the records


def test_index_walks_the_cold_storage_alone() -> None:
    """Only the cold storage knows every record, so the cache is left out of the walk."""
    hot, cold, storage = cached()
    cold.push("cold.json", b"{}")
    hot.push("hot.json", b"{}")
    quiet(hot, cold)
    assert sorted(storage.index()) == ["cold.json"]
    # a prefix is handed to the cold storage, still in a single walk and still without the cache
    assert list(storage.index(prefix="cold")) == ["cold.json"]
    assert cold.calls == {"index": 2}
    assert hot.calls == {}


# removing


def test_remove_clears_both_storages() -> None:
    """Removing a record clears the cached copy along with the stored one."""
    hot, cold, storage = cached()
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    storage.remove("data.json")
    assert stored(hot, "data.json") is None
    assert stored(cold, "data.json") is None
    assert cold.calls == {"exists": 1, "remove": 1}
    assert hot.calls == {"exists": 1, "remove": 1}


def test_remove_of_an_uncached_record_leaves_the_cache_alone() -> None:
    """Removing a record absent from the cache touches the cold storage only."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    storage.remove("data.json")
    assert stored(cold, "data.json") is None
    assert cold.calls == {"exists": 1, "remove": 1}
    assert hot.calls == {"exists": 1}


# a write the cold storage does not take


def test_push_leaves_nothing_cached_when_the_cold_storage_refuses() -> None:
    """A record the cold storage never took is dropped, not left cached as an uncommitted write."""
    hot, cold, storage = cached()
    cold.push = refuse  # type: ignore[method-assign]
    quiet(hot, cold)
    with pytest.raises(RuntimeError, match="cold storage is down"):
        storage.push("data.json", b"{}")
    assert stored(hot, "data.json") is None
    assert hot.calls["push"] == 1
    assert hot.calls["remove"] == 1


def test_a_refused_forced_push_leaves_the_stored_record_readable() -> None:
    """A forced push the cold storage refuses costs the cached copy, never the stored one."""
    _, cold, storage = cached()
    storage.push("data.json", b"{}")
    cold.push = refuse  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="cold storage is down"):
        storage.push("data.json", b"[]", force=True)
    # the cache may lose its copy, but the record the cold storage still holds is served
    assert storage.pull("data.json") == b"{}"


# a cache holding what the cold storage does not


def test_a_stale_cached_record_is_served_as_is() -> None:
    """The cache is trusted for what it holds: a diverged copy is served without a second look."""
    hot, cold, storage = cached()
    cold.push("data.json", b"{}")
    hot.push("data.json", b"[]")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"[]"
    assert storage.size("data.json") == len(b"[]")
    assert cold.calls == {}


def test_a_record_only_in_the_cache_does_not_block_a_push() -> None:
    """Whether a record exists is the cold storage's to answer, the cache holding no authority.

    A copy left in the cache of a record the cold storage does not hold must not turn an
    ordinary push into a refusal: there would be no way to store the record at all.
    """
    hot, _, storage = cached()
    hot.push("data.json", b"[]")
    quiet(hot)
    storage.push("data.json", b"{}", force=True)
    assert storage.pull("data.json") == b"{}"


def test_binary_storages_are_cached(tmp_path: Path) -> None:
    """A cache over byte storages of different kinds stores and serves records whole."""
    hot: Storage[bytes] = MemoryStorage()
    cold: Storage[bytes] = LocalStorage(tmp_path)
    storage = CachedStorage(hot, cold)
    storage.push("nested/data.json", b"{}")
    assert (tmp_path / "nested/data.json").is_file()
    assert hot.pull("nested/data.json") == b"{}"
    assert storage.pull("nested/data.json") == b"{}"
    hot.remove("nested/data.json")
    assert storage.pull("nested/data.json") == b"{}"


def test_stream_storages_are_cached(tmp_path: Path) -> None:
    """A cache over stream storages stores records whole, and warms itself back from the cold."""
    hot = StreamLocalStorage(tmp_path / "hot")
    cold = StreamLocalStorage(tmp_path / "cold")
    storage = CachedStorage(hot, cold)
    with (tmp_path / "source.json").open("wb") as source:
        source.write(b"{}")
    with (tmp_path / "source.json").open("rb") as source:
        storage.push("data.json", source)
    assert (tmp_path / "cold/data.json").read_bytes() == b"{}"
    assert (tmp_path / "hot/data.json").read_bytes() == b"{}"
    hot.remove("data.json")
    with storage.pull("data.json") as record:
        assert record.read() == b"{}"
    assert (tmp_path / "hot/data.json").read_bytes() == b"{}"
