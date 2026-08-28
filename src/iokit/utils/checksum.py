__all__ = ["Hash"]

import hashlib
from collections.abc import Callable
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
    XXH3_64 = "xxh3_64"
    XXH3_128 = "xxh3_128"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA224 = "sha224"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_224 = "sha3_224"
    SHA3_256 = "sha3_256"
    SHA3_384 = "sha3_384"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"

    @property
    def algorithm(self) -> _HashAlgorithm:
        return _FACTORIES[self]()

    def digest(self, buffer: BinaryIO, *, chunk_size: int = CHUNK_SIZE) -> bytes:
        algorithm = self.algorithm
        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break
            algorithm.update(chunk)
        return algorithm.digest()


_FACTORIES: dict[Hash, Callable[[], _HashAlgorithm]] = {
    Hash.XXH32: xxhash.xxh32,
    Hash.XXH64: xxhash.xxh64,
    Hash.XXH128: xxhash.xxh128,
    Hash.XXH3_64: xxhash.xxh3_64,
    Hash.XXH3_128: xxhash.xxh3_128,
    Hash.MD5: hashlib.md5,
    Hash.SHA1: hashlib.sha1,
    Hash.SHA224: hashlib.sha224,
    Hash.SHA256: hashlib.sha256,
    Hash.SHA384: hashlib.sha384,
    Hash.SHA512: hashlib.sha512,
    Hash.SHA3_224: hashlib.sha3_224,
    Hash.SHA3_256: hashlib.sha3_256,
    Hash.SHA3_384: hashlib.sha3_384,
    Hash.SHA3_512: hashlib.sha3_512,
    Hash.BLAKE2B: hashlib.blake2b,
    Hash.BLAKE2S: hashlib.blake2s,
}
