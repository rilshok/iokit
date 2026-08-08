"""Utilities for working with S3 buckets."""

__all__ = [
    "S3Storage",
    "StreamS3Storage",
]
import threading
from collections.abc import Iterator
from typing import Any, BinaryIO

import boto3
from botocore import UNSIGNED

from .storage import BinaryStorage, Storage


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


class StreamS3Storage(Storage[BinaryIO]):
    """A simple S3 client."""

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
        if not config:
            config["config"] = boto3.session.Config(signature_version=UNSIGNED)
        self._get_client = BotoClientFactory("s3", config)

    @property
    def _client(self) -> object:
        return self._get_client()

    def _uid_parts(self, uid: str) -> dict[str, str]:
        """Address an object in the storage bucket by its UID."""
        return {"Bucket": self._bucket, "Key": f"{self._folder}{uid}"}

    def pull(self, uid: str) -> BinaryIO:
        """Pull an object from S3 and return its body as a file-like object."""
        try:
            response = self._client.get_object(**self._uid_parts(uid))

        except self._client.exceptions.NoSuchKey as exc:
            msg = f"State not found, {uid=!r}."
            raise FileNotFoundError(msg) from exc

        else:
            return response["Body"]

    def exists(self, uid: str) -> bool:
        """Check if an object exists in S3."""
        try:
            self._client.head_object(**self._uid_parts(uid))

        except self._client.exceptions.ClientError as exc:
            match exc.response.get("Error", {}).get("Code"):
                case "404":
                    return False
                case other:
                    msg = f"Unexpected error. Error code: {other}). {exc}"
                    raise RuntimeError(msg) from exc

        else:
            return True

    def size(self, uid: str) -> int:
        """Return the size in bytes of an object in S3."""
        try:
            response = self._client.head_object(**self._uid_parts(uid))

        except self._client.exceptions.ClientError as exc:
            match exc.response.get("Error", {}).get("Code"):
                case "404":
                    msg = f"State not found, {uid=!r}."
                    raise FileNotFoundError(msg) from exc
                case other:
                    msg = f"Unexpected error. Error code: {other}). {exc}"
                    raise RuntimeError(msg) from exc

        else:
            return int(response["ContentLength"])

    def push(self, uid: str, record: BinaryIO, *, force: bool = False) -> None:
        """Push a file-like object to S3."""
        if not force and self.exists(uid=uid):
            msg = f"State already exists, {uid=!r}"
            raise FileExistsError(msg)

        try:
            self._client.upload_fileobj(Fileobj=record, **self._uid_parts(uid))

        except self._client.exceptions.ClientError as exc:
            msg = f"Failed to upload object, {uid=!r}"
            match exc.response.get("Error", {}).get("Code"):
                case "AccessDenied":
                    msg = f"{msg}, access denied."
                    raise PermissionError(msg) from exc

                case other:
                    msg = f"{msg}, unexpected error code: {other}"
                    raise RuntimeError(msg) from exc

    def remove(self, uid: str) -> None:
        """Remove an object from S3."""
        if not self.exists(uid=uid):
            msg = f"State not found, {uid=!r}."
            raise FileNotFoundError(msg)

        try:
            self._client.delete_object(**self._uid_parts(uid))

        except self._client.exceptions.ClientError as exc:
            msg = f"Failed to remove object, {uid=!r}"
            match exc.response.get("Error", {}).get("Code"):
                case "AccessDenied":
                    msg = f"{msg}, access denied."
                    raise PermissionError(msg) from exc

                case other:
                    msg = f"{msg}, unexpected error code: {other}"
                    raise RuntimeError(msg) from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List objects in an S3."""
        paginator = self._client.get_paginator("list_objects_v2")
        options: dict[str, str] = {"Bucket": self._bucket}
        full_prefix = f"{self._folder}{prefix or ''}"
        if full_prefix:
            options["Prefix"] = full_prefix
        offset = len(self._folder)
        for page in paginator.paginate(**options):
            if page["KeyCount"] == 0:
                return
            yield from (obj["Key"][offset:] for obj in page["Contents"])


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
