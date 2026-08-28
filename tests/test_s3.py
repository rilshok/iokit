"""The one smoke test reaching a real service, over the anonymous NOAA GEFS open-data bucket.

Everything else about S3 is covered without the network: `tests/test_s3_service.py` against
a served stand-in bucket, and `tests/test_s3_compatibility.py` against services that stray
from the protocol. What is left here is what only a real service can answer for: that an
unsigned client reaches a public bucket at all, and that the object it serves arrives whole.

See https://registry.opendata.aws/noaa-gefs/ for the dataset description.
"""

import pytest

from iokit.storage.s3 import StreamS3Storage

BUCKET = "noaa-gefs-pds"
FOLDER = "gefs.20170101/00"
NAME = "gec00.t00z.pgrb2aanl.idx"
UID = f"{FOLDER}/{NAME}"
SIZE = 3411

#: the only module reaching a real service, and the only one needing the network to pass
pytestmark = pytest.mark.network


def test_a_public_bucket_is_read_without_credentials() -> None:
    storage = StreamS3Storage(BUCKET)
    assert storage.exists(UID)
    assert storage.size(UID) == SIZE
    with storage.pull(UID) as stream:
        data = stream.read()
    assert len(data) == SIZE
    assert data.startswith(b"1:0:d=2017010100:HGT:10 mb:anl:")


def test_a_public_bucket_is_listed_without_credentials() -> None:
    storage = StreamS3Storage(BUCKET, FOLDER)
    assert list(storage.index(NAME)) == [NAME]
