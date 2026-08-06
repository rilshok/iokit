__all__ = ["ChecksumMixin"]

import hashlib
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from enum import Enum
from io import BytesIO
from typing import BinaryIO, Protocol

import xxhash

CHUNK_SIZE = 32768


class _HashAlgorithm(Protocol):
    def update(self, data: bytes, /) -> None: ...

    def digest(self) -> bytes: ...

    def hexdigest(self) -> str: ...


class Hash(Enum):
    XXH32 = "xxh32"
    XXH64 = "xxh64"
    XXH128 = "xxh128"
    SHA256 = "sha256"
    MD5 = "md5"
    SHA1 = "sha1"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"

    @property
    def algorithm(self) -> _HashAlgorithm:  # noqa: PLR0911
        match self:
            case Hash.XXH32:
                return xxhash.xxh32()
            case Hash.XXH64:
                return xxhash.xxh64()
            case Hash.XXH128:
                return xxhash.xxh128()
            case Hash.SHA256:
                return hashlib.sha256()
            case Hash.MD5:
                return hashlib.md5()  # noqa: S324
            case Hash.SHA1:
                return hashlib.sha1()  # noqa: S324
            case Hash.BLAKE2B:
                return hashlib.blake2b()
            case Hash.BLAKE2S:
                return hashlib.blake2s()

    def digest(self, buffer: BinaryIO, *, chunk_size: int = CHUNK_SIZE) -> bytes:
        algorithm = self.algorithm
        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break
            algorithm.update(chunk)
        return algorithm.digest()


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


def _hexdigest(algorithm: Hash, data: object) -> str:
    hash_object = algorithm.algorithm
    for chunk in _iterate_chuncks(data):
        hash_object.update(chunk)
    return hash_object.hexdigest()


class ChecksumMixin:
    def hexdigest(self, algorithm: Hash) -> str:
        return _hexdigest(algorithm=algorithm, data=self)

    def hexdigest_assert(self, algorithm: Hash, hexdigest: str) -> None:
        if (checksum := self.hexdigest(algorithm)) != hexdigest:
            msg = f"Expected {algorithm} {hexdigest =}, got ={checksum!r}"
            raise AssertionError(msg)
