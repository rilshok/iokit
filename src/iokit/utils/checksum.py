__all__ = ["Hash"]

import hashlib
from enum import Enum
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
