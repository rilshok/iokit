"""The contract every byte storage is expected to keep, checked on each implementation."""

from typing import TYPE_CHECKING

import pytest

from iokit.storage import (
    BinaryStorage,
    CachedStorage,
    CountingStorage,
    LocalStorage,
    MemoryStorage,
    Storage,
    StreamMemoryStorage,
    is_record_uid,
    validate_uid,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tests.conftest import S3Service

BACKENDS = ["cached", "counting", "local", "memory", "s3", "s3-folder", "stream-memory"]


@pytest.fixture(params=BACKENDS, name="storage")
def storage_fixture(request: pytest.FixtureRequest) -> Storage[bytes]:
    """An empty storage of every kind the contract below is expected to hold for."""
    match request.param:
        case "memory":
            return MemoryStorage()
        case "stream-memory":
            return BinaryStorage(StreamMemoryStorage())
        case "local":
            return LocalStorage(request.getfixturevalue("tmp_path"))
        case "counting":
            return CountingStorage(MemoryStorage())
        case "cached":
            # a memory cache in front of a local storage, the two kinds it is meant to bridge
            return CachedStorage(MemoryStorage(), LocalStorage(request.getfixturevalue("tmp_path")))
        case "s3" | "s3-folder" as kind:
            s3 = pytest.importorskip("iokit.storage.s3", reason="boto3 is needed to reach an S3")
            service: S3Service = request.getfixturevalue("s3_service")
            folder = "nested/folder" if kind == "s3-folder" else None
            return s3.S3Storage(
                service.bucket(),
                folder,
                access_key=service.access_key,
                secret_access_key=service.secret_access_key,
                endpoint_url=service.endpoint_url,
                region_name=service.region_name,
            )
        case name:
            raise NotImplementedError(name)


UIDS = [
    "data.bin",
    "reports/first.bin",
    "deeply/nested/under/many/levels.bin",
    "имя-файла.bin",
    "name with spaces.bin",
    ".secret",
    "reports/.secret",
]


@pytest.mark.parametrize("uid", UIDS)
def test_a_pushed_record_is_indexed_under_the_uid_it_was_pushed_with(
    storage: Storage[bytes],
    uid: str,
) -> None:
    storage.push(uid, b"hello")
    assert list(storage.index()) == [uid]


@pytest.mark.parametrize("uid", UIDS)
def test_a_pushed_record_is_reachable_by_the_uid_it_was_pushed_with(
    storage: Storage[bytes],
    uid: str,
) -> None:
    storage.push(uid, b"hello")
    assert storage.exists(uid)
    assert storage.pull(uid) == b"hello"
    assert storage.size(uid) == 5


@pytest.mark.parametrize(
    "record",
    [b"", b"\x00", b"\x00binary\xff\xfe", bytes(range(256)), b"x" * 100_000],
)
def test_a_record_survives_a_roundtrip_byte_for_byte(
    storage: Storage[bytes],
    record: bytes,
) -> None:
    storage.push("data.bin", record)
    assert storage.pull("data.bin") == record
    assert storage.size("data.bin") == len(record)


def test_a_forced_push_replaces_the_record_whole(storage: Storage[bytes]) -> None:
    storage.push("data.bin", b"a long record that is about to be replaced")
    storage.push("data.bin", b"short", force=True)
    assert storage.pull("data.bin") == b"short"
    assert storage.size("data.bin") == 5


def test_a_refused_push_leaves_the_record_untouched(storage: Storage[bytes]) -> None:
    storage.push("data.bin", b"hello")
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.bin", b"other")
    assert storage.pull("data.bin") == b"hello"


def test_a_record_can_be_pushed_again_after_a_remove(storage: Storage[bytes]) -> None:
    storage.push("reports/first.bin", b"hello")
    storage.remove("reports/first.bin")
    assert not storage.exists("reports/first.bin")
    assert list(storage.index()) == []
    storage.push("reports/first.bin", b"world")
    assert storage.pull("reports/first.bin") == b"world"


def test_a_missing_record_raises_file_not_found(storage: Storage[bytes]) -> None:
    assert not storage.exists("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.size("missing.bin")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.remove("missing.bin")


def test_index_lists_every_record_once(storage: Storage[bytes]) -> None:
    uids = [f"reports/{index:03d}.bin" for index in range(25)]
    for uid in uids:
        storage.push(uid, b"hello")
    listed = list(storage.index())
    assert sorted(listed) == uids
    assert len(listed) == len(uids)


def test_index_is_filtered_by_prefix(storage: Storage[bytes]) -> None:
    storage.push("report.bin", b"a")
    storage.push("reports/first.bin", b"b")
    storage.push("notes.bin", b"c")
    # a prefix is a string prefix of the uid, not a directory
    assert sorted(storage.index(prefix="report")) == ["report.bin", "reports/first.bin"]
    assert sorted(storage.index(prefix="reports/")) == ["reports/first.bin"]
    assert list(storage.index(prefix="nothing")) == []


def test_index_survives_records_changing_under_it(storage: Storage[bytes]) -> None:
    storage.push("first.bin", b"a")
    storage.push("second.bin", b"b")
    seen: list[str] = []
    walk: Iterator[str] = storage.index()
    for uid in walk:
        seen.append(uid)
        storage.remove(uid)
        storage.push(f"{uid}.copy", b"c")
    assert sorted(seen) == ["first.bin", "second.bin"]
    assert sorted(storage.index()) == ["first.bin.copy", "second.bin.copy"]


def test_a_directory_shaped_uid_is_not_a_record(storage: Storage[bytes]) -> None:
    storage.push("reports/first.bin", b"hello")
    assert not storage.exists("reports")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        storage.pull("reports")


#: what every call refuses a uid with
NO_RECORD = "is not a relative path naming a record"

BAD_UIDS = [
    "",
    ".",
    "..",
    "./data.bin",
    "data.bin/",
    "reports//first.bin",
    "/data.bin",
    "reports/./first.bin",
    "reports/../first.bin",
]


@pytest.mark.parametrize("uid", BAD_UIDS)
def test_a_uid_no_record_could_be_handed_back_under_is_refused(
    storage: Storage[bytes],
    uid: str,
) -> None:
    """Every call naming such a uid is refused, and none of them leaves a record behind."""
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.push(uid, b"hello")
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.pull(uid)
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.size(uid)
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.remove(uid)
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.exists(uid)
    assert list(storage.index()) == []


@pytest.mark.parametrize("uid", ["data.bin", "reports/first.bin", ".secret", "имя.bin"])
def test_validate_uid_accepts_what_a_storage_hands_back(uid: str) -> None:
    assert is_record_uid(uid)
    assert validate_uid(uid) == tuple(uid.split("/"))


@pytest.mark.parametrize("uid", BAD_UIDS)
def test_validate_uid_refuses_what_no_storage_could_hand_back(uid: str) -> None:
    assert not is_record_uid(uid)
    with pytest.raises(ValueError, match=NO_RECORD):
        validate_uid(uid)
