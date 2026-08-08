"""Read-only smoke tests against the anonymous NOAA GEFS open-data bucket.

See https://registry.opendata.aws/noaa-gefs/ for the dataset description.
"""

from itertools import islice

import pytest

from iokit.storage.s3 import StreamS3Storage

BUCKET = "noaa-gefs-pds"
FOLDER = "gefs.20170101/00"
NAME = "gec00.t00z.pgrb2aanl.idx"
UID = f"{FOLDER}/{NAME}"
SIZE = 3411
MISSING = "definitely/missing.key"


@pytest.fixture
def storage() -> StreamS3Storage:
    return StreamS3Storage(BUCKET)


@pytest.fixture
def folder_storage() -> StreamS3Storage:
    return StreamS3Storage(BUCKET, FOLDER)


def test_exists(storage: StreamS3Storage) -> None:
    assert storage.exists(UID)
    assert not storage.exists(MISSING)


def test_size(storage: StreamS3Storage) -> None:
    assert storage.size(UID) == SIZE


def test_pull(storage: StreamS3Storage) -> None:
    with storage.pull(UID) as stream:
        data = stream.read()
    assert len(data) == SIZE
    assert data.startswith(b"1:0:d=2017010100:HGT:10 mb:anl:")


def test_index(storage: StreamS3Storage) -> None:
    assert list(islice(storage.index(UID), 2)) == [UID]


def test_index_of_missing_prefix(storage: StreamS3Storage) -> None:
    assert list(storage.index(MISSING)) == []


def test_folder_is_stripped_from_index(folder_storage: StreamS3Storage) -> None:
    assert list(islice(folder_storage.index(NAME), 2)) == [NAME]


def test_folder_is_prepended_to_uid(folder_storage: StreamS3Storage) -> None:
    assert folder_storage.exists(NAME)
    assert folder_storage.size(NAME) == SIZE


@pytest.mark.parametrize("folder", ["", "/", FOLDER, f"/{FOLDER}/"])
def test_folder_is_normalized(folder: str) -> None:
    storage = StreamS3Storage(BUCKET, folder)
    uid = NAME if folder.strip("/") else UID
    assert storage.size(uid) == SIZE


def test_pull_of_missing_raises(storage: StreamS3Storage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.pull(MISSING)


def test_size_of_missing_raises(storage: StreamS3Storage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.size(MISSING)


def test_remove_of_missing_raises(storage: StreamS3Storage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.remove(MISSING)
