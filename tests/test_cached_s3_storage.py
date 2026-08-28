"""A local cache in front of a bucket, the one arrangement the cache is built for.

The cache itself is covered in `tests/test_cached_storage.py`, over storages that hand out
records the caller can read twice. A bucket does not: its record arrives as a stream of the
response, readable once and never again, so what is worth checking here is that such a
record survives the trip into the cache and back out of it.
"""

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

import pytest

from iokit import CachedStorage, CountingStorage, StreamLocalStorage
from iokit.storage.s3 import StreamS3Storage

if TYPE_CHECKING:
    from tests.conftest import S3Service

UID = "reports/first.bin"
RECORD = b"hello"

Counted = CountingStorage[BinaryIO]


@pytest.fixture(name="hot")
def hot_fixture(tmp_path: Path) -> Counted:
    """A counted local storage, empty and writable, standing in front of the bucket."""
    return CountingStorage(StreamLocalStorage(tmp_path))


@pytest.fixture(name="cold")
def cold_fixture(s3_service: "S3Service") -> Counted:
    """A counted view of a bucket holding one record, to tell how much traffic it sees."""
    backend = StreamS3Storage(
        s3_service.bucket(),
        access_key=s3_service.access_key,
        secret_access_key=s3_service.secret_access_key,
        endpoint_url=s3_service.endpoint_url,
        region_name=s3_service.region_name,
    )
    backend.push(UID, BytesIO(RECORD))
    return CountingStorage(backend)


@pytest.fixture(name="storage")
def storage_fixture(hot: Counted, cold: Counted) -> CachedStorage[BinaryIO]:
    return CachedStorage(hot, cold)


def test_a_record_read_from_the_bucket_is_cached_whole(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
) -> None:
    """The response is read once, and what the caller gets is the copy left in the cache."""
    with storage.pull(UID) as record:
        assert record.read() == RECORD
    assert hot.backend.size(UID) == len(RECORD)


def test_a_cached_record_is_read_without_the_bucket(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
    cold: Counted,
) -> None:
    """A second read is served locally, the bucket not asked for the record again."""
    with storage.pull(UID) as record:
        record.read()
    hot.reset()
    cold.reset()
    with storage.pull(UID) as record:
        assert record.read() == RECORD
    assert cold.calls == {}
    assert hot.calls == {"exists": 1, "pull": 1}


def test_a_pushed_record_reaches_the_bucket_and_the_cache(
    storage: CachedStorage[BinaryIO],
    hot: Counted,
    cold: Counted,
) -> None:
    """A pushed stream is uploaded and cached alike, neither side getting a drained one."""
    storage.push("second.bin", BytesIO(b"world"))
    with cold.backend.pull("second.bin") as record:
        assert record.read() == b"world"
    with hot.backend.pull("second.bin") as record:
        assert record.read() == b"world"
