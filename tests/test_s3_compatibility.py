"""How the S3 client copes with services that stray from the protocol, every reply a stand-in.

See `tests/test_s3.py` for the smoke tests against a real bucket.
"""

from collections.abc import Iterator
from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError

from iokit.storage.s3 import StreamS3Storage

BUCKET = "bucket"
UID = "folder/object.txt"
SIZE = 3411
#: what every call refuses a uid no record could be handed back under with
NO_RECORD = "is not a relative path naming a record"

Reply = Any


def error(operation: str, code: str = "", status: int = 0) -> ClientError:
    """Build the error botocore raises for a given reply of a service."""
    response = {
        "Error": {"Code": code, "Message": "something the service said"},
        "ResponseMetadata": {"HTTPStatusCode": status},
    }
    return ClientError(response, operation)


#: a HEAD answered with something that cannot mean anything, as some services do
BAD_REQUEST = error("HeadObject", code="400", status=400)
DENIED = error("HeadObject", code="AccessDenied", status=403)
MISSING = error("GetObject", code="NoSuchKey", status=404)
BROKEN = error("GetObject", code="InternalError", status=500)
NO_MULTIPART = error("CreateMultipartUpload", code="NotImplemented", status=501)
NO_LIST_V2 = error("ListObjectsV2", code="NotImplemented", status=501)


class FakePaginator:
    """The pages a listing call answers with, or the error it fails with."""

    def __init__(self, reply: Reply) -> None:
        self._reply = reply

    def paginate(self, **_: object) -> Iterator[Any]:
        if isinstance(self._reply, BaseException):
            raise self._reply
        yield from self._reply


class FakeS3:
    """A stand-in service, answering each call with a value to return or an error to raise."""

    def __init__(self, **replies: Reply) -> None:
        self._replies = replies
        self.calls: list[str] = []
        self.received: dict[str, dict[str, object]] = {}

    def _reply(self, operation: str, **kwargs: object) -> Reply:
        self.calls.append(operation)
        self.received[operation] = kwargs
        reply = self._replies.get(operation)
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def head_object(self, **kwargs: object) -> Reply:
        return self._reply("head_object", **kwargs)

    def get_object(self, **kwargs: object) -> Reply:
        return self._reply("get_object", **kwargs)

    def put_object(self, **kwargs: object) -> Reply:
        return self._reply("put_object", **kwargs)

    def upload_fileobj(self, **kwargs: object) -> Reply:
        return self._reply("upload_fileobj", **kwargs)

    def delete_object(self, **kwargs: object) -> Reply:
        return self._reply("delete_object", **kwargs)

    def get_paginator(self, operation: str) -> FakePaginator:
        return FakePaginator(self._reply(operation))


def served_by(client: FakeS3, folder: str | None = None) -> StreamS3Storage:
    """Point a storage at a stand-in service instead of a real bucket."""
    storage = StreamS3Storage(BUCKET, folder)
    storage._get_client = lambda: client  # noqa: SLF001
    return storage


def ranged(total: int, *, content_range: bool = True) -> dict[str, Any]:
    """The reply of a service to a read of the first byte of an object."""
    reply: dict[str, Any] = {"Body": BytesIO(b"x"), "ContentLength": 1 if content_range else total}
    if content_range:
        reply["ContentRange"] = f"bytes 0-0/{total}"
    return reply


# a service whose HEAD replies cannot be trusted


def test_size_falls_back_to_a_ranged_read() -> None:
    """A HEAD that makes no sense is not the last word on the size of an object."""
    client = FakeS3(head_object=BAD_REQUEST, get_object=ranged(SIZE))
    assert served_by(client).size(UID) == SIZE
    assert client.calls == ["head_object", "get_object"]


def test_ranged_read_falls_back_to_the_content_length() -> None:
    """A service that ignores the range still reports how much it is about to send."""
    client = FakeS3(head_object=BAD_REQUEST, get_object=ranged(SIZE, content_range=False))
    assert served_by(client).size(UID) == SIZE


def test_ranged_read_leaves_no_stream_open() -> None:
    """The body of the fallback read is dropped, having been asked for its length alone."""
    reply = ranged(SIZE)
    served_by(FakeS3(head_object=BAD_REQUEST, get_object=reply)).size(UID)
    assert reply["Body"].closed


def test_size_of_an_empty_object_is_zero() -> None:
    """An object without bytes has no first byte to read, and a size all the same."""
    unsatisfiable = error("GetObject", code="InvalidRange", status=416)
    client = FakeS3(head_object=BAD_REQUEST, get_object=unsatisfiable)
    assert served_by(client).size(UID) == 0


def test_size_of_missing_when_nothing_is_said() -> None:
    """Two replies that carry no meaning are read as the likeliest thing: no such object."""
    client = FakeS3(head_object=BAD_REQUEST, get_object=error("GetObject", status=400))
    with pytest.raises(FileNotFoundError):
        served_by(client).size(UID)


def test_fallback_finds_nothing() -> None:
    client = FakeS3(head_object=BAD_REQUEST, get_object=MISSING)
    assert not served_by(client).exists(UID)


def test_fallback_finds_the_object() -> None:
    client = FakeS3(head_object=BAD_REQUEST, get_object=ranged(SIZE))
    assert served_by(client).exists(UID)


def test_a_standard_head_costs_a_single_call() -> None:
    """A service that answers a HEAD properly is never read a second time."""
    client = FakeS3(head_object={"ContentLength": SIZE})
    assert served_by(client).size(UID) == SIZE
    assert client.calls == ["head_object"]


def test_a_standard_absence_costs_a_single_call() -> None:
    """A plain 404 is a definite answer, so there is nothing to double-check."""
    client = FakeS3(head_object=error("HeadObject", code="404", status=404))
    assert not served_by(client).exists(UID)
    assert client.calls == ["head_object"]


# a service that refuses the request


def test_denied_head_is_reported() -> None:
    """A refusal must not pass for an absence, or a push would overwrite unseen data."""
    with pytest.raises(PermissionError):
        served_by(FakeS3(head_object=DENIED)).exists(UID)


def test_denied_head_is_not_retried() -> None:
    """There is nothing a ranged read could add once the service has said no."""
    client = FakeS3(head_object=DENIED)
    with pytest.raises(PermissionError):
        served_by(client).size(UID)
    assert client.calls == ["head_object"]


def test_denied_pull_is_reported() -> None:
    with pytest.raises(PermissionError):
        served_by(FakeS3(get_object=DENIED)).pull(UID)


def test_denied_push_is_reported() -> None:
    denied = error("PutObject", code="AccessDenied", status=403)
    client = FakeS3(head_object=MISSING, upload_fileobj=denied)
    with pytest.raises(PermissionError):
        served_by(client).push(UID, BytesIO(b"data"))


def test_denied_remove_is_reported() -> None:
    denied = error("DeleteObject", code="AccessDenied", status=403)
    client = FakeS3(head_object={"ContentLength": SIZE}, delete_object=denied)
    with pytest.raises(PermissionError):
        served_by(client).remove(UID)


def test_denied_listing_is_reported() -> None:
    denied = error("ListObjectsV2", code="AccessDenied", status=403)
    with pytest.raises(PermissionError):
        list(served_by(FakeS3(list_objects_v2=denied)).index())


def test_denial_names_bucket_and_uid() -> None:
    """The message has to be enough to go and fix the policy that caused it."""
    with pytest.raises(PermissionError, match="AccessDenied") as failure:
        served_by(FakeS3(get_object=DENIED)).pull(UID)
    assert BUCKET in str(failure.value)
    assert UID in str(failure.value)


# a service that is merely broken


def test_failing_service_is_not_an_absence() -> None:
    """A service in trouble says nothing about whether the object is there."""
    with pytest.raises(RuntimeError, match="InternalError"):
        served_by(FakeS3(get_object=BROKEN)).pull(UID)


def test_failing_head_is_not_an_absence() -> None:
    client = FakeS3(head_object=error("HeadObject", status=503), get_object=BROKEN)
    with pytest.raises(RuntimeError):
        served_by(client).size(UID)


# a service without managed transfers


def test_push_falls_back_to_a_single_request() -> None:
    """An upload the service could not make sense of is retried the simplest way."""
    client = FakeS3(head_object=MISSING, upload_fileobj=NO_MULTIPART, put_object={})
    served_by(client).push(UID, BytesIO(b"data"))
    assert client.calls == ["head_object", "upload_fileobj", "put_object"]


def test_push_rewinds_the_record_before_the_fallback() -> None:
    """The failed attempt has read the record, so the retry starts over from the front."""
    client = FakeS3(head_object=MISSING, upload_fileobj=NO_MULTIPART, put_object={})
    record = BytesIO(b"data")
    record.read()
    served_by(client).push(UID, record)
    assert client.received["put_object"]["Body"].read() == b"data"


def test_push_reports_what_the_fallback_ran_into() -> None:
    denied = error("PutObject", code="AccessDenied", status=403)
    client = FakeS3(head_object=MISSING, upload_fileobj=NO_MULTIPART, put_object=denied)
    with pytest.raises(PermissionError):
        served_by(client).push(UID, BytesIO(b"data"))


def test_push_of_an_existing_object_is_refused() -> None:
    client = FakeS3(head_object={"ContentLength": SIZE})
    with pytest.raises(FileExistsError):
        served_by(client).push(UID, BytesIO(b"data"))


# a service with an older listing api


def test_listing_reads_pages_without_a_key_count() -> None:
    """The count of a page is optional, and some services leave it out."""
    pages = [{"Contents": [{"Key": "a"}, {"Key": "b"}]}, {"Contents": [{"Key": "c"}]}]
    assert list(served_by(FakeS3(list_objects_v2=pages)).index()) == ["a", "b", "c"]


def test_listing_of_an_empty_bucket_yields_nothing() -> None:
    assert list(served_by(FakeS3(list_objects_v2=[{}])).index()) == []


def test_listing_falls_back_to_the_older_api() -> None:
    """A service that never implemented the second version still has a first one."""
    pages = [{"Contents": [{"Key": "a"}]}]
    client = FakeS3(list_objects_v2=NO_LIST_V2, list_objects=pages)
    assert list(served_by(client).index()) == ["a"]
    assert client.calls == ["list_objects_v2", "list_objects"]


def test_listing_does_not_repeat_itself() -> None:
    """A listing that broke halfway is reported, rather than started over on the older api."""

    def pages() -> Iterator[dict[str, Any]]:
        yield {"Contents": [{"Key": "a"}]}
        raise NO_LIST_V2

    client = FakeS3(list_objects_v2=pages(), list_objects=[{"Contents": [{"Key": "a"}]}])
    with pytest.raises(RuntimeError):
        list(served_by(client).index())


def test_listing_strips_the_folder_of_the_storage() -> None:
    pages = [{"Contents": [{"Key": "folder/a"}, {"Key": "folder/b"}]}]
    storage = served_by(FakeS3(list_objects_v2=pages), folder="folder")
    assert list(storage.index()) == ["a", "b"]


# a uid that names no record


def test_bad_uid_never_reaches_the_service() -> None:
    """Which uid names no record is settled in the contract; here, none is sent anywhere."""
    client = FakeS3()
    storage = served_by(client)
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.pull("./object.txt")
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.size("./object.txt")
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.exists("./object.txt")
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.remove("./object.txt")
    assert client.calls == []


def test_bad_uid_uploads_nothing() -> None:
    client = FakeS3(head_object=MISSING)
    storage = served_by(client)
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.push("./object.txt", BytesIO(b"hello"))
    assert client.calls == []


def test_uid_stays_within_the_folder() -> None:
    """The folder is the root a uid is relative to, so it may not be escaped with '..'."""
    client = FakeS3()
    storage = served_by(client, "folder")
    with pytest.raises(ValueError, match=NO_RECORD):
        storage.exists("../elsewhere/object.txt")
    assert client.calls == []
