"""A local cache in front of the anonymous NOAA GEFS open-data bucket.

The cold storage is read-only, so the tests cover the reading half of the cache and the
refusal the writing half runs into. See https://registry.opendata.aws/noaa-gefs/ for the
dataset description.
"""

from itertools import islice
from pathlib import Path
from typing import BinaryIO

import pytest

from iokit.storage import CachedStorage, CountingStorage
from iokit.storage.local import StreamLocalStorage
from iokit.storage.s3 import StreamS3Storage

BUCKET = "noaa-gefs-pds"
FOLDER = "gefs.20170101/00"
NAME = "gec00.t00z.pgrb2aanl.idx"
UID = f"{FOLDER}/{NAME}"
SIZE = 3411
HEAD = b"1:0:d=2017010100:HGT:10 mb:anl:"
MISSING = "definitely/missing.key"

Counted = CountingStorage[BinaryIO]


@pytest.fixture
def hot(tmp_path: Path) -> Counted:
    """A counted local storage, empty and writable, standing in front of the bucket."""
    return CountingStorage(StreamLocalStorage(tmp_path))


@pytest.fixture
def cold() -> Counted:
    """A counted anonymous view of the bucket, to tell how much traffic it sees."""
    return CountingStorage(StreamS3Storage(BUCKET))


@pytest.fixture
def storage(hot: Counted, cold: Counted) -> CachedStorage[BinaryIO]:
    return CachedStorage(hot, cold)


def quiet(*storages: Counted) -> None:
    """Forget the traffic of the arrangement, so that a test counts only what it acts on."""
    for storage in storages:
        storage.reset()


# reading through the cache


def test_pull_returns_the_record(storage: CachedStorage[BinaryIO]) -> None:
    """A record read through the cache is the one the bucket holds, streamed as it is."""
    with storage.pull(UID) as record:
        data = record.read()
    assert len(data) == SIZE
    assert data.startswith(HEAD)


def test_pull_caches_the_record(storage: CachedStorage[BinaryIO], hot: Counted) -> None:
    """A record read through the cache is left behind in the local storage, whole."""
    with storage.pull(UID) as record:
        record.read()
    assert hot.backend.exists(UID)
    assert hot.backend.size(UID) == SIZE


def test_a_cached_record_is_read_without_the_bucket(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
    cold: Counted,
) -> None:
    """Once cached, a record is served locally, the bucket not asked for it again."""
    with storage.pull(UID) as record:
        record.read()
    quiet(hot, cold)
    with storage.pull(UID) as record:
        assert record.read().startswith(HEAD)
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "pull": 1}


def test_pull_of_missing_raises(storage: CachedStorage[BinaryIO], hot: Counted) -> None:
    """A record the bucket does not hold is refused, leaving nothing behind in the cache."""
    with pytest.raises(FileNotFoundError):
        storage.pull(MISSING)
    assert not hot.backend.exists(MISSING)


# asking about a record


def test_exists_falls_back_to_the_bucket(
    storage: CachedStorage[BinaryIO],
    cold: Counted,
) -> None:
    """A record absent from the cache is looked up in the bucket."""
    assert storage.exists(UID)
    assert not storage.exists(MISSING)
    assert cold.calls == {"exists": 2}


def test_a_cached_record_exists_without_the_bucket(
    storage: CachedStorage[BinaryIO],
    cold: Counted,
) -> None:
    """Once cached, a record is known to exist locally, the bucket not asked."""
    with storage.pull(UID) as record:
        record.read()
    quiet(cold)
    assert storage.exists(UID)
    assert cold.calls == {}


def test_size_falls_back_to_the_bucket(
    storage: CachedStorage[BinaryIO],
    cold: Counted,
) -> None:
    """The size of a record absent from the cache is asked of the bucket."""
    assert storage.size(UID) == SIZE
    assert cold.calls == {"size": 1}


def test_a_cached_record_is_sized_without_the_bucket(
    storage: CachedStorage[BinaryIO],
    cold: Counted,
) -> None:
    """Once cached, a record is sized locally, the bucket not asked."""
    with storage.pull(UID) as record:
        record.read()
    quiet(cold)
    assert storage.size(UID) == SIZE
    assert cold.calls == {}


def test_size_of_missing_raises(storage: CachedStorage[BinaryIO]) -> None:
    """A record neither storage holds has no size to give."""
    with pytest.raises(FileNotFoundError):
        storage.size(MISSING)


# walking the index


def test_index_walks_the_bucket(storage: CachedStorage[BinaryIO], cold: Counted) -> None:
    """The index is the bucket's, the cache adding nothing to the walk."""
    assert list(islice(storage.index(UID), 2)) == [UID]
    assert cold.calls == {"index": 1}


def test_index_ignores_what_only_the_cache_holds(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
    tmp_path: Path,
) -> None:
    """A record living only in the cache is not indexed, the bucket knowing nothing of it."""
    with (tmp_path / "source.bin").open("wb") as source:
        source.write(b"{}")
    with (tmp_path / "source.bin").open("rb") as source:
        hot.backend.push("local.bin", source)
    assert list(storage.index("local.bin")) == []


# writing against a read-only bucket


def test_push_is_refused_by_the_bucket(
    storage: CachedStorage[BinaryIO],
    tmp_path: Path,
) -> None:
    """A bucket that takes no writes refuses the push, the cache not covering for it."""
    with (tmp_path / "source.bin").open("wb") as source:
        source.write(b"{}")
    with (tmp_path / "source.bin").open("rb") as source, pytest.raises(PermissionError):
        storage.push("pushed.bin", source)


def test_a_refused_push_leaves_nothing_cached(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
    tmp_path: Path,
) -> None:
    """A record the bucket never took is not left behind in the cache."""
    with (tmp_path / "source.bin").open("wb") as source:
        source.write(b"{}")
    with (tmp_path / "source.bin").open("rb") as source, pytest.raises(PermissionError):
        storage.push("pushed.bin", source)
    assert not hot.backend.exists("pushed.bin")


def test_remove_is_refused_by_the_bucket(storage: CachedStorage[BinaryIO]) -> None:
    """Removing a record the bucket holds is refused, the bucket taking no deletions."""
    with pytest.raises(PermissionError):
        storage.remove(UID)


def test_remove_of_missing_raises(storage: CachedStorage[BinaryIO]) -> None:
    """A record neither storage holds cannot be removed."""
    with pytest.raises(FileNotFoundError):
        storage.remove(MISSING)
