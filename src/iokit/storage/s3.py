"""Utilities for working with S3 buckets."""

__all__ = [
    "S3Storage",
    "StreamS3Storage",
]
import threading
from collections.abc import Iterator
from enum import Enum, auto
from typing import Any, BinaryIO

import boto3
from botocore import UNSIGNED
from botocore.exceptions import ClientError

from .storage import BinaryStorage, Storage

_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_RANGE_NOT_SATISFIABLE = 416
_HTTP_SERVER_ERROR = 500

#: Error codes that only ever mean the caller is not allowed to do what it asked for.
_DENIED_CODES = frozenset(
    {
        "accessdenied",
        "accessdeniedexception",
        "accountproblem",
        "allaccessdisabled",
        "authorizationheadermalformed",
        "credentialsnotsupported",
        "expiredtoken",
        "forbidden",
        "invalidaccesskeyid",
        "invalidsecurity",
        "invalidtoken",
        "missingauthenticationtoken",
        "missingsecurityheader",
        "signaturedoesnotmatch",
        "tokenrefreshrequired",
        "unauthorized",
        "unauthorizedaccess",
    },
)

#: Error codes that only ever mean the addressed object is not there.
_MISSING_CODES = frozenset(
    {
        "keynotfound",
        "nosuchbucket",
        "nosuchkey",
        "nosuchobject",
        "nosuchversion",
        "notfound",
        "objectnotfound",
    },
)

#: Error codes that mean the service does not offer the call, whatever status carries them.
_UNSUPPORTED_CODES = frozenset(
    {
        "invalidrequest",
        "methodnotallowed",
        "notimplemented",
        "unsupportedoperation",
    },
)

#: Error codes that only ever mean the service itself is unhappy, not the request.
_FAILURE_CODES = frozenset(
    {
        "internalerror",
        "internalfailure",
        "operationaborted",
        "requesttimeout",
        "serviceunavailable",
        "slowdown",
        "throttling",
        "toomanyrequests",
    },
)

#: List operations to try, most capable first, for services stuck on the older API.
_LIST_OPERATIONS = ("list_objects_v2", "list_objects")


class _Reason(Enum):
    """What a failed request most likely says about the storage."""

    DENIED = auto()
    MISSING = auto()
    FAILURE = auto()
    UNKNOWN = auto()


def _error_code(exc: ClientError) -> str:
    """Return the error code the service reported, or an empty string."""
    error: dict[str, Any] = exc.response.get("Error") or {}
    return str(error.get("Code") or "")


def _status_code(exc: ClientError) -> int:
    """Return the HTTP status the service replied with, or zero."""
    metadata: dict[str, Any] = exc.response.get("ResponseMetadata") or {}
    try:
        return int(metadata.get("HTTPStatusCode") or 0)
    except (TypeError, ValueError):
        return 0


def _classify(exc: ClientError) -> _Reason:
    """Tell what a failed request means, as far as the reply allows.

    S3-compatible services disagree on what they answer, so only unambiguous codes and
    statuses are trusted here; everything else stays `_Reason.UNKNOWN` and is left for the
    caller to interpret in the context of the operation it was performing.
    """
    code = _error_code(exc).lower()
    status = _status_code(exc)
    if code in _DENIED_CODES or status in (_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN):
        return _Reason.DENIED
    if code in _MISSING_CODES or status == _HTTP_NOT_FOUND:
        return _Reason.MISSING
    if code in _UNSUPPORTED_CODES:
        return _Reason.UNKNOWN
    if code in _FAILURE_CODES or status >= _HTTP_SERVER_ERROR:
        return _Reason.FAILURE
    return _Reason.UNKNOWN


def _detail(exc: ClientError) -> str:
    """Describe what the service replied, for an error message."""
    parts: list[str] = []
    code = _error_code(exc)
    if code:
        parts.append(f"code {code}")
    status = _status_code(exc)
    if status:
        parts.append(f"HTTP {status}")
    return ", ".join(parts) or "no error code"


def _is_empty_range(exc: ClientError) -> bool:
    """Check whether a ranged read failed because the object holds no bytes."""
    if _status_code(exc) == _HTTP_RANGE_NOT_SATISFIABLE:
        return True
    return _error_code(exc).lower() in ("invalidrange", "requestedrangenotsatisfiable")


def _total_size(response: dict[str, Any]) -> int:
    """Read the full object size out of the reply to a ranged read."""
    body = response.get("Body")
    if body is not None:
        body.close()
    total = str(response.get("ContentRange") or "").rpartition("/")[2].strip()
    if total.isdigit():
        return int(total)
    return int(response["ContentLength"])


class StreamS3Storage(Storage[BinaryIO]):
    """A simple S3 client.

    The client is deliberately forgiving about what an S3-compatible service answers: many
    of them stray from the protocol, and a reply that cannot be understood is read as the
    most likely thing it could mean for the operation at hand. A reply that unmistakably
    speaks of access rights is the exception, and is always reported as a `PermissionError`,
    never quietly turned into an absent object.
    """

    def __init__(  # noqa: PLR0913
        self,
        bucket: str,
        folder: str | None = None,
        *,
        access_key: str | None = None,
        secret_access_key: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        self._bucket = bucket
        folder = (folder or "").strip("/")
        self._folder = f"{folder}/" if folder else ""
        config: dict[str, Any] = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_access_key,
            "endpoint_url": endpoint_url,
            "region_name": region_name,
        }
        config = {k: v for k, v in config.items() if v is not None}
        options: dict[str, Any] = {"retries": {"max_attempts": 5, "mode": "standard"}}
        if not config:
            options["signature_version"] = UNSIGNED
        config["config"] = boto3.session.Config(**options)
        self._get_client = BotoClientFactory("s3", config)

    @property
    def _client(self) -> object:
        return self._get_client()

    def _uid_parts(self, uid: str) -> dict[str, str]:
        """Address an object in the storage bucket by its UID."""
        return {"Bucket": self._bucket, "Key": f"{self._folder}{uid}"}

    def _failure(
        self,
        exc: ClientError,
        *,
        subject: str,
        action: str,
        assume: _Reason,
    ) -> Exception:
        """Build the exception a failed request deserves.

        Args:
            exc: The error the service replied with.
            subject: What was addressed, rendered for the message.
            action: What was being attempted, as a verb phrase.
            assume: What to make of a reply that carries no usable meaning.

        Returns:
            A `PermissionError`, a `FileNotFoundError` or a `RuntimeError`, ready to raise.
        """
        reason = _classify(exc)
        if reason is _Reason.UNKNOWN:
            reason = assume
        detail = _detail(exc)
        match reason:
            case _Reason.DENIED:
                msg = (
                    f"Access denied while trying to {action}, {subject}, "
                    f"bucket={self._bucket!r} ({detail}). Check the credentials, "
                    f"the bucket policy and the object permissions."
                )
                return PermissionError(msg)
            case _Reason.MISSING:
                msg = f"State not found, {subject} ({detail})."
                return FileNotFoundError(msg)
            case _:
                msg = f"Failed to {action}, {subject}, bucket={self._bucket!r} ({detail}). {exc}"
                return RuntimeError(msg)

    def pull(self, uid: str) -> BinaryIO:
        """Pull an object from S3 and return its body as a file-like object.

        Args:
            uid: UID of the object to read.

        Returns:
            The body of the object, as a file-like object.

        Raises:
            PermissionError: The service refused to serve the object.
            FileNotFoundError: The object is not there, as far as the service let on.
            RuntimeError: The service failed to answer the request.
        """
        try:
            response = self._client.get_object(**self._uid_parts(uid))

        except ClientError as exc:
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="read the object",
                assume=_Reason.MISSING,
            )
            raise failure from exc

        else:
            return response["Body"]

    def exists(self, uid: str) -> bool:
        """Check if an object exists in S3.

        A service that refuses the request is reported rather than believed: a missing
        permission must not pass for a missing object, or a push would overwrite what it
        was not allowed to look at.

        Args:
            uid: UID of the object to look for.

        Returns:
            Whether the object is there.

        Raises:
            PermissionError: The service refused to answer for the object.
            RuntimeError: The service failed to answer the request.
        """
        try:
            self.size(uid)

        except FileNotFoundError:
            return False

        else:
            return True

    def size(self, uid: str) -> int:
        """Return the size in bytes of an object in S3.

        Args:
            uid: UID of the object to measure.

        Returns:
            The size of the object in bytes.

        Raises:
            PermissionError: The service refused to answer for the object.
            FileNotFoundError: The object is not there, as far as the service let on.
            RuntimeError: The service failed to answer the request.
        """
        try:
            response = self._client.head_object(**self._uid_parts(uid))

        except ClientError as exc:
            if _classify(exc) is _Reason.UNKNOWN:
                return self._size_by_range(uid)
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="inspect the object",
                assume=_Reason.MISSING,
            )
            raise failure from exc

        else:
            return int(response["ContentLength"])

    def _size_by_range(self, uid: str) -> int:
        """Measure an object with a ranged read, where a HEAD reply made no sense.

        Args:
            uid: UID of the object to measure.

        Returns:
            The size of the object in bytes.

        Raises:
            PermissionError: The service refused to serve the object.
            FileNotFoundError: The object is not there, as far as the service let on.
            RuntimeError: The service failed to answer the request.
        """
        try:
            response = self._client.get_object(**self._uid_parts(uid), Range="bytes=0-0")

        except ClientError as exc:
            if _is_empty_range(exc):
                return 0
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="measure the object",
                assume=_Reason.MISSING,
            )
            raise failure from exc

        else:
            return _total_size(response)

    def push(self, uid: str, record: BinaryIO, *, force: bool = False) -> None:
        """Push a file-like object to S3.

        Args:
            uid: UID to store the object under.
            record: The body to upload.
            force: Whether to overwrite an object already stored under `uid`.

        Raises:
            FileExistsError: An object is already stored under `uid` and `force` is unset.
            PermissionError: The service refused the upload.
            RuntimeError: The service failed to store the object.
        """
        if not force and self.exists(uid=uid):
            msg = f"State already exists, {uid=!r}"
            raise FileExistsError(msg)

        try:
            self._client.upload_fileobj(Fileobj=record, **self._uid_parts(uid))

        except ClientError as exc:
            if _classify(exc) is _Reason.UNKNOWN and record.seekable():
                self._put_whole(uid, record)
                return
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="upload the object",
                assume=_Reason.FAILURE,
            )
            raise failure from exc

    def _put_whole(self, uid: str, record: BinaryIO) -> None:
        """Upload an object in a single request, for services without managed transfers.

        Args:
            uid: UID to store the object under.
            record: The body to upload, rewound before it is sent.

        Raises:
            PermissionError: The service refused the upload.
            RuntimeError: The service failed to store the object.
        """
        record.seek(0)
        try:
            self._client.put_object(Body=record, **self._uid_parts(uid))

        except ClientError as exc:
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="upload the object",
                assume=_Reason.FAILURE,
            )
            raise failure from exc

    def remove(self, uid: str) -> None:
        """Remove an object from S3.

        Args:
            uid: UID of the object to remove.

        Raises:
            FileNotFoundError: The object is not there, as far as the service let on.
            PermissionError: The service refused to remove the object.
            RuntimeError: The service failed to remove the object.
        """
        if not self.exists(uid=uid):
            msg = f"State not found, {uid=!r}."
            raise FileNotFoundError(msg)

        try:
            self._client.delete_object(**self._uid_parts(uid))

        except ClientError as exc:
            failure = self._failure(
                exc,
                subject=f"{uid=!r}",
                action="remove the object",
                assume=_Reason.FAILURE,
            )
            raise failure from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List objects in an S3.

        Args:
            prefix: Beginning of the UIDs to list, within the storage folder.

        Returns:
            The UIDs stored under `prefix`, in the order the service reports them.

        Raises:
            PermissionError: The service refused to list the bucket.
            RuntimeError: The service failed to list the bucket.
        """
        offset = len(self._folder)
        keys = self._iter_keys(f"{self._folder}{prefix or ''}")
        return (key[offset:] for key in keys)

    def _iter_keys(self, prefix: str) -> Iterator[str]:
        """Iterate over the raw keys of a bucket, over whichever list API answers.

        Args:
            prefix: Beginning of the keys to list, including the storage folder.

        Yields:
            The keys stored under `prefix`.

        Raises:
            PermissionError: The service refused to list the bucket.
            RuntimeError: The service failed to list the bucket.
        """
        options: dict[str, str] = {"Bucket": self._bucket}
        if prefix:
            options["Prefix"] = prefix
        last = len(_LIST_OPERATIONS) - 1
        for attempt, operation in enumerate(_LIST_OPERATIONS):
            listed = False
            try:
                for page in self._client.get_paginator(operation).paginate(**options):
                    for obj in page.get("Contents") or ():
                        listed = True
                        yield str(obj["Key"])

            except ClientError as exc:
                spent = listed or attempt == last
                if spent or _classify(exc) is not _Reason.UNKNOWN:
                    failure = self._failure(
                        exc,
                        subject=f"{prefix=!r}",
                        action="list the bucket",
                        assume=_Reason.FAILURE,
                    )
                    raise failure from exc

            else:
                return


class BotoClientFactory:
    def __init__(self, resource: str, config: dict[str, Any]) -> None:
        self._lock = threading.Lock()
        self._count = 0
        self._threshold = 1000
        self._resource = resource
        self._config = config
        self._client = self._create()

    def _create(self) -> object:
        return boto3.client(self._resource, **self._config)

    def __call__(self) -> object:
        with self._lock:
            if self._count > self._threshold:
                self._client = self._create()
                self._count = 0
            else:
                self._count += 1
            return self._client


class S3Storage(BinaryStorage):
    def __init__(  # noqa: PLR0913
        self,
        bucket: str,
        folder: str | None = None,
        *,
        access_key: str | None = None,
        secret_access_key: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        backend = StreamS3Storage(
            bucket,
            folder,
            access_key=access_key,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )
        super().__init__(backend)
