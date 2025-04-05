__all__ = ["ChecksumMixin"]

import hashlib
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from io import BytesIO
from typing import Literal, Protocol

import xxhash

CHUNK_SIZE = 4096

HashAlgorithm = Literal["xxh32", "xxh64", "xxh128", "sha256", "md5", "sha1", "blake2b", "blake2s"]


class _HashAlgorithmProtocol(Protocol):
    def hexdigest(self) -> str:
        pass

    def update(self, data: bytes) -> None:
        pass


def _get_hash_algorithm(algorithm: HashAlgorithm) -> _HashAlgorithmProtocol:  # noqa: PLR0911
    match algorithm:
        case "xxh32":
            return xxhash.xxh32()
        case "xxh64":
            return xxhash.xxh64()
        case "xxh128":
            return xxhash.xxh128()
        case "sha256":
            return hashlib.sha256()
        case "md5":
            return hashlib.md5()  # noqa: S324
        case "sha1":
            return hashlib.sha1()  # noqa: S324
        case "blake2b":
            return hashlib.blake2b()
        case "blake2s":
            return hashlib.blake2s()
        case other:
            msg = f"Unknown hash algorithm '{other}'"
            raise ValueError(msg)


@contextmanager
def _buffer(data: object) -> Generator[BytesIO, None, None]:
    close = False
    if hasattr(data, "buffer"):
        buffer = data.buffer
        close = True
    elif isinstance(data, bytes):
        buffer = BytesIO(data)
        close = True
    elif hasattr(data, "data"):
        data = data.data
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
    data: object,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    with _buffer(data) as buffer:
        yield from iter(lambda: buffer.read(chunk_size), b"")


def _hexdigest(algorithm: HashAlgorithm, data: object) -> str:
    hash_object = _get_hash_algorithm(algorithm)
    for chunk in _iterate_chuncks(data):
        hash_object.update(chunk)
    return hash_object.hexdigest()


class ChecksumMixin:
    def hexdigest(self, algorithm: HashAlgorithm) -> str:
        return _hexdigest(algorithm=algorithm, data=self)

    def hexdigest_assert(self, algorithm: HashAlgorithm, hexdigest: str) -> None:
        if (checksum := self.hexdigest(algorithm)) != hexdigest:
            msg = f"Expected {algorithm} {hexdigest =}, got ={checksum!r}"
            raise AssertionError(msg)
