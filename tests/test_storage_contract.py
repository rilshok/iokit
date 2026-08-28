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


#: what a uid may look like: nested, unicode, spaced, hidden - a record is a record
UIDS = [
    "data.bin",
    "reports/first.bin",
    "deeply/nested/under/many/levels.bin",
    "имя-файла.bin",
    "name with spaces.bin",
    ".secret",
    "reports/.secret",
]

#: what a record may hold: nothing, a lone zero, arbitrary bytes, and more than a buffer's worth
RECORDS = [b"", b"\x00", b"\x00binary\xff\xfe", bytes(range(256)), b"x" * 100_000]

#: what every call refuses a uid with
NO_RECORD = "is not a relative path naming a record"

#: neither a uid that names nothing, nor one that could name something outside the storage
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


def test_a_record_is_filed_under_the_uid_it_was_pushed_with(storage: Storage[bytes]) -> None:
    """A uid is the whole address of a record, and uids of every shape live side by side."""
    for uid in UIDS:
        storage.push(uid, uid.encode())
    assert sorted(storage.index()) == sorted(UIDS)
    for uid in UIDS:
        assert storage.exists(uid)
        assert storage.pull(uid) == uid.encode()
        assert storage.size(uid) == len(uid.encode())


def test_a_record_survives_a_roundtrip_byte_for_byte(storage: Storage[bytes]) -> None:
    """A storage keeps bytes, not text: nothing is added, trimmed or translated on the way."""
    for index, record in enumerate(RECORDS):
        uid = f"record-{index}.bin"
        storage.push(uid, record)
        assert storage.pull(uid) == record
        assert storage.size(uid) == len(record)


def test_a_record_is_replaced_only_when_the_push_is_forced(storage: Storage[bytes]) -> None:
    """A push is safe by default: it refuses before writing, so nothing is lost unasked."""
    storage.push("data.bin", b"a long record that is about to be replaced")
    with pytest.raises(FileExistsError, match="already exists"):
        storage.push("data.bin", b"other")
    assert storage.pull("data.bin") == b"a long record that is about to be replaced"
    storage.push("data.bin", b"short", force=True)
    assert storage.pull("data.bin") == b"short"
    assert storage.size("data.bin") == 5


def test_a_record_can_be_pushed_again_after_a_remove(storage: Storage[bytes]) -> None:
    """Removing leaves nothing behind, not even the directory a nested uid seemed to need."""
    storage.push("reports/first.bin", b"hello")
    storage.remove("reports/first.bin")
    assert not storage.exists("reports/first.bin")
    assert list(storage.index()) == []
    storage.push("reports/first.bin", b"world")
    assert storage.pull("reports/first.bin") == b"world"


def test_a_uid_that_names_no_record_is_a_missing_record(storage: Storage[bytes]) -> None:
    """Nothing is invented for a uid that holds no record, a directory-shaped one included."""
    storage.push("reports/first.bin", b"hello")
    for uid in ("missing.bin", "reports"):
        assert not storage.exists(uid)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            storage.pull(uid)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            storage.size(uid)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            storage.remove(uid)


def test_the_index_lists_every_record_once_and_narrows_to_a_prefix(
    storage: Storage[bytes],
) -> None:
    """A prefix is a prefix of the uid, not a directory, so it may cut a name in half."""
    uids = [f"reports/{index:03d}.bin" for index in range(25)]
    for uid in [*uids, "report.bin", "notes.bin"]:
        storage.push(uid, b"hello")
    listed = list(storage.index())
    assert sorted(listed) == sorted([*uids, "report.bin", "notes.bin"])
    assert len(listed) == len(uids) + 2
    assert sorted(storage.index(prefix="reports/")) == uids
    assert sorted(storage.index(prefix="report")) == sorted([*uids, "report.bin"])
    assert list(storage.index(prefix="nothing")) == []


def test_the_index_survives_records_changing_under_it(storage: Storage[bytes]) -> None:
    """A walk may be acted on as it goes: what it yields has been settled by then."""
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


def test_a_uid_no_record_could_be_handed_back_under_is_refused(storage: Storage[bytes]) -> None:
    """Every call refuses such a uid, and none of them leaves anything behind."""
    for uid in BAD_UIDS:
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


@pytest.mark.parametrize("uid", UIDS)
def test_validate_uid_accepts_what_a_storage_hands_back(uid: str) -> None:
    """The rule itself, which every storage above leans on."""
    assert is_record_uid(uid)
    assert validate_uid(uid) == tuple(uid.split("/"))


@pytest.mark.parametrize("uid", BAD_UIDS)
def test_validate_uid_refuses_what_no_storage_could_hand_back(uid: str) -> None:
    assert not is_record_uid(uid)
    with pytest.raises(ValueError, match=NO_RECORD):
        validate_uid(uid)
