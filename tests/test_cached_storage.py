"""A cache in front of a storage: which side answers a call, and at what cost in traffic.

A cache over records readable only once is in `tests/test_cached_s3_storage.py`.
"""

from pathlib import Path

import pytest

from iokit import (
    CachedStorage,
    CountingStorage,
    LocalStorage,
    MemoryStorage,
    StreamLocalStorage,
)

Counted = CountingStorage[bytes]


@pytest.fixture(name="hot")
def hot_fixture() -> Counted:
    """The cache, empty, counting every call it is asked to answer."""
    return CountingStorage(MemoryStorage())


@pytest.fixture(name="cold")
def cold_fixture() -> Counted:
    """The storage behind the cache, counted the same way."""
    return CountingStorage(MemoryStorage())


@pytest.fixture(name="storage")
def storage_fixture(hot: Counted, cold: Counted) -> CachedStorage[bytes]:
    return CachedStorage(hot, cold)


def quiet(*storages: Counted) -> None:
    """Forget the traffic of the arrangement, so that a test counts only what it acts on."""
    for storage in storages:
        storage.reset()


def stored(storage: Counted, uid: str) -> bytes | None:
    """Read a record straight from the counted storage, without counting the lookup."""
    backend = storage.backend
    return backend.pull(uid) if backend.exists(uid) else None


def unavailable(*_args: object, **_kwargs: object) -> None:
    """Stand in for the push of a cold storage that is down."""
    msg = "cold storage is down"
    raise RuntimeError(msg)


# pushing


def test_push_reaches_both(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """A pushed record lands in the cache and in the cold storage alike."""
    storage.push("data.json", b"{}")
    assert stored(hot, "data.json") == b"{}"
    assert stored(cold, "data.json") == b"{}"


def test_push_writes_cold_once(
    storage: CachedStorage[bytes],
    cold: Counted,
) -> None:
    """Pushing costs the cold storage one existence lookup and one write, no more."""
    storage.push("data.json", b"{}")
    assert cold.calls == {"exists": 1, "push": 1}


def test_forced_push_skips_the_lookup(
    storage: CachedStorage[bytes],
    cold: Counted,
) -> None:
    """A forced push goes straight to writing, asking the cold storage nothing beforehand."""
    storage.push("data.json", b"{}", force=True)
    assert cold.calls == {"push": 1}


def test_push_refuses_to_overwrite_without_force(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """An unforced push over an existing record refuses before writing anything anywhere."""
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.json", b"[]")
    assert cold.calls == {"exists": 1}
    assert stored(cold, "data.json") == b"{}"
    assert stored(hot, "data.json") is None


def test_forced_push_overwrites_both(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """A forced push replaces the record on both sides, leaving no stale copy cached."""
    storage.push("data.json", b"{}")
    storage.push("data.json", b"[]", force=True)
    assert stored(hot, "data.json") == b"[]"
    assert stored(cold, "data.json") == b"[]"


# pulling


def test_pull_warms_the_cache(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """A record missing from the cache is read from the cold storage and cached on the way out."""
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert stored(hot, "data.json") == b"{}"
    # the cold storage is read once, and never asked whether the record is there
    assert cold.calls == {"pull": 1}


def test_warmed_record_skips_the_cold(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Once warmed, a record is served without the cold storage hearing about it."""
    cold.push("data.json", b"{}")
    assert storage.pull("data.json") == b"{}"
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "pull": 1}


def test_pushed_record_skips_the_cold(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Pushing warms the cache too, so reading a record back never reaches the cold storage."""
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert cold.calls == {}


def test_missing_pull_caches_nothing(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """A read that finds nothing leaves the cache as empty as it was."""
    with pytest.raises(FileNotFoundError):
        storage.pull("missing.json")
    assert stored(hot, "missing.json") is None
    assert cold.calls == {"pull": 1}
    assert hot.calls == {"exists": 1}


def test_dropped_record_is_warmed_back(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Evicting the cached copy behind the cache's back costs a read, never the record."""
    storage.push("data.json", b"{}")
    hot.backend.remove("data.json")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"{}"
    assert stored(hot, "data.json") == b"{}"
    assert cold.calls == {"pull": 1}


# asking after a record


def test_exists_answered_by_the_cache(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """A cached record is known to exist without asking the cold storage."""
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.exists("data.json")
    assert cold.calls == {}
    assert hot.calls == {"exists": 1}


def test_exists_falls_back(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """What the cache has never seen is looked up in the cold storage, present or not."""
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.exists("data.json")
    assert not storage.exists("missing.json")
    assert cold.calls == {"exists": 2}
    assert hot.calls == {"exists": 2}


def test_size_answered_by_the_cache(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """The size of a cached record is measured on the cache, the two copies being alike."""
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.size("data.json") == len(b"{}")
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "size": 1}


def test_size_falls_back_in_one_lookup(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Sizing an uncached record asks the cold storage once and does not pull it into the cache."""
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    assert storage.size("data.json") == len(b"{}")
    assert stored(hot, "data.json") is None
    assert cold.calls == {"size": 1}
    assert hot.calls == {"exists": 1}


# walking the records


def test_index_walks_the_cold_alone(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Only the cold storage knows every record, so the cache is left out of the walk."""
    cold.push("cold.json", b"{}")
    hot.push("hot.json", b"{}")
    quiet(hot, cold)
    assert sorted(storage.index()) == ["cold.json"]
    # a prefix is handed to the cold storage, still in a single walk and still without the cache
    assert list(storage.index(prefix="cold")) == ["cold.json"]
    assert cold.calls == {"index": 2}
    assert hot.calls == {}


# removing


def test_remove_clears_both(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Removing a record clears the cached copy along with the stored one."""
    storage.push("data.json", b"{}")
    quiet(hot, cold)
    storage.remove("data.json")
    assert stored(hot, "data.json") is None
    assert stored(cold, "data.json") is None
    assert cold.calls == {"exists": 1, "remove": 1}
    assert hot.calls == {"exists": 1, "remove": 1}


def test_remove_uncached_skips_the_cache(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """Removing a record absent from the cache touches the cold storage only."""
    cold.push("data.json", b"{}")
    quiet(hot, cold)
    storage.remove("data.json")
    assert stored(cold, "data.json") is None
    assert cold.calls == {"exists": 1, "remove": 1}
    assert hot.calls == {"exists": 1}


# a write the cold storage does not take


def test_refused_push_caches_nothing(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record the cold storage never took is dropped, not left cached as an uncommitted write."""
    monkeypatch.setattr(cold, "push", unavailable)
    quiet(hot, cold)
    with pytest.raises(RuntimeError, match="cold storage is down"):
        storage.push("data.json", b"{}")
    assert stored(hot, "data.json") is None
    assert hot.calls["push"] == 1
    assert hot.calls["remove"] == 1


def test_refused_forced_push_keeps_the_record(
    storage: CachedStorage[bytes],
    cold: Counted,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forced push the cold storage refuses costs the cached copy, never the stored one."""
    storage.push("data.json", b"{}")
    monkeypatch.setattr(cold, "push", unavailable)
    with pytest.raises(RuntimeError, match="cold storage is down"):
        storage.push("data.json", b"[]", force=True)
    # the cache may lose its copy, but the record the cold storage still holds is served
    assert storage.pull("data.json") == b"{}"


# a cache holding what the cold storage does not


def test_stale_cache_is_served_as_is(
    storage: CachedStorage[bytes],
    hot: Counted,
    cold: Counted,
) -> None:
    """The cache is trusted for what it holds: a diverged copy is served without a second look."""
    cold.push("data.json", b"{}")
    hot.push("data.json", b"[]")
    quiet(hot, cold)
    assert storage.pull("data.json") == b"[]"
    assert storage.size("data.json") == len(b"[]")
    assert cold.calls == {}


def test_cache_does_not_block_a_push(
    storage: CachedStorage[bytes],
    hot: Counted,
) -> None:
    """Whether a record exists is the cold storage's to answer, the cache has no say."""
    hot.push("data.json", b"[]")
    quiet(hot)
    storage.push("data.json", b"{}", force=True)
    assert storage.pull("data.json") == b"{}"


# storages of other kinds


def test_byte_storages_are_cached(tmp_path: Path) -> None:
    """A cache over byte storages of different kinds stores and serves records whole."""
    hot = MemoryStorage()
    cold = LocalStorage(tmp_path)
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
    (tmp_path / "source.json").write_bytes(b"{}")
    with (tmp_path / "source.json").open("rb") as source:
        storage.push("data.json", source)
    assert (tmp_path / "cold/data.json").read_bytes() == b"{}"
    assert (tmp_path / "hot/data.json").read_bytes() == b"{}"
    hot.remove("data.json")
    with storage.pull("data.json") as record:
        assert record.read() == b"{}"
    assert (tmp_path / "hot/data.json").read_bytes() == b"{}"
