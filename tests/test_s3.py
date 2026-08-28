"""The one smoke test reaching a real service: an unsigned client over a public bucket.

Everything else about S3 is covered without the network, in `tests/test_s3_service.py` and
`tests/test_s3_compatibility.py`. See https://registry.opendata.aws/noaa-gefs/ for the dataset.
"""

import pytest

from iokit.storage.s3 import StreamS3Storage

BUCKET = "noaa-gefs-pds"
FOLDER = "gefs.20170101/00"
NAME = "gec00.t00z.pgrb2aanl.idx"
UID = f"{FOLDER}/{NAME}"
SIZE = 3411

#: the only module reaching a real service, which the network is needed to reach
pytestmark = pytest.mark.network


def test_public_bucket_is_read() -> None:
    storage = StreamS3Storage(BUCKET)
    assert storage.exists(UID)
    assert storage.size(UID) == SIZE
    with storage.pull(UID) as stream:
        data = stream.read()
    assert len(data) == SIZE
    assert data.startswith(b"1:0:d=2017010100:HGT:10 mb:anl:")


def test_public_bucket_is_listed() -> None:
    storage = StreamS3Storage(BUCKET, FOLDER)
    assert list(storage.index(NAME)) == [NAME]
