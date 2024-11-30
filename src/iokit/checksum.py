__all__ = ["ChecksumMixin"]

import hashlib
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from io import BytesIO
from typing import Any, Literal

import xxhash

CHUNK_SIZE = 4096

HashAlgorithm = Literal["xxh32", "xxh64", "xxh128", "sha256", "md5", "sha1"]


@contextmanager
def _buffer(data: Any) -> Generator[BytesIO, None, None]:
    close = False
    if hasattr(data, "buffer"):
        buffer = data.buffer
        assert isinstance(buffer, BytesIO)
        close = True
    elif isinstance(data, bytes):
        buffer = BytesIO(data)
        close = True
    elif hasattr(data, "data"):
        data = data.data
        assert isinstance(data, bytes)
        buffer = BytesIO(data.data)
        close = True
    else:
        buffer = data
        buffer.seek(0)

    try:
        yield buffer

    finally:
        if close:
            buffer.close()


def _iterate_chuncks(
    data: Any,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    with _buffer(data) as buffer:
        yield from iter(lambda: buffer.read(chunk_size), b"")


def _hexdigest(algorithm: Any, data: Any) -> str:
    for chunk in _iterate_chuncks(data):
        algorithm.update(chunk)
    return algorithm.hexdigest()


class ChecksumMixin:
    @property
    def _hexdigest_xxh32(self) -> str:
        return _hexdigest(algorithm=xxhash.xxh32(), data=self)

    @property
    def _hexdigest_xxh64(self) -> str:
        return _hexdigest(algorithm=xxhash.xxh64(), data=self)

    @property
    def _hexdigest_xxh128(self) -> str:
        return _hexdigest(algorithm=xxhash.xxh128(), data=self)

    @property
    def _hexdigest_sha256(self) -> str:
        return _hexdigest(algorithm=hashlib.sha256(), data=self)

    @property
    def _hexdigest_md5(self) -> str:
        return _hexdigest(algorithm=hashlib.md5(), data=self)

    @property
    def _hexdigest_sha1(self) -> str:
        return _hexdigest(algorithm=hashlib.sha1(), data=self)

    def hexdigest(self, algorithm: HashAlgorithm = "xxh64") -> str:
        match algorithm:
            case "xxh32":
                return self._hexdigest_xxh32
            case "xxh64":
                return self._hexdigest_xxh64
            case "xxh128":
                return self._hexdigest_xxh128
            case "sha256":
                return self._hexdigest_sha256
            case "md5":
                return self._hexdigest_md5
            case "sha1":
                return self._hexdigest_sha1
            case other:
                msg = f"Unknown hash algorithm '{other}'"
                raise ValueError(msg)

    def hexdigest_assert(self, algorithm: HashAlgorithm, hexdigest: str) -> None:
        if (checksum := self.hexdigest(algorithm)) != hexdigest:
            msg = f"Expected {algorithm} {hexdigest =}, got ={checksum!r}"
            raise AssertionError(msg)
