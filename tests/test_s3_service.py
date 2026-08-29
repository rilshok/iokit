"""What a folder does to a uid on the way in and on the way out, over a bucket on localhost.

The contract every storage keeps is in `tests/test_storage_contract.py`.
"""

from io import BytesIO
from typing import TYPE_CHECKING

import pytest

from iokit.storage.s3 import StreamS3Storage

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.conftest import S3Service

FOLDER = "reports"
NAME = "first.bin"
UID = f"{FOLDER}/{NAME}"
RECORD = b"hello"


@pytest.fixture(name="served")
def served_fixture(s3_service: "S3Service") -> "Callable[..., StreamS3Storage]":
    """A way to open a storage over a bucket of its own, holding one record under `UID`."""
    bucket = s3_service.bucket()

    def serve(folder: str | None = None) -> StreamS3Storage:
        return StreamS3Storage(
            bucket,
            folder,
            access_key=s3_service.access_key,
            secret_access_key=s3_service.secret_access_key,
            endpoint_url=s3_service.endpoint_url,
            region_name=s3_service.region_name,
        )

    serve().push(UID, BytesIO(RECORD))
    return serve


def test_folder_is_prepended(served: "Callable[..., StreamS3Storage]") -> None:
    """Inside a folder, a uid is read relative to it, and names nothing outside it."""
    storage = served(FOLDER)
    assert storage.exists(NAME)
    assert storage.size(NAME) == len(RECORD)
    with storage.pull(NAME) as record:
        assert record.read() == RECORD
    assert not storage.exists(UID)


def test_folder_is_stripped_from_the_index(served: "Callable[..., StreamS3Storage]") -> None:
    """A record is listed under the uid it is reachable by, the folder left out of it."""
    assert list(served().index()) == [UID]
    assert list(served(FOLDER).index()) == [NAME]


@pytest.mark.parametrize("folder", ["", "/", FOLDER, f"/{FOLDER}/", f"//{FOLDER}//"])
def test_slashes_around_a_folder(
    served: "Callable[..., StreamS3Storage]",
    folder: str,
) -> None:
    """However a folder is spelled, it names the same records."""
    storage = served(folder)
    uid = NAME if folder.strip("/") else UID
    assert storage.size(uid) == len(RECORD)
