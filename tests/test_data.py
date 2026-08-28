import hashlib
from collections.abc import Callable

import pytest
import xxhash

from iokit import Data
from iokit.utils.checksum import Hash

PAYLOAD = b"the quick brown fox jumps over the lazy dog"

REFERENCES: dict[Hash, Callable[[bytes], bytes]] = {
    Hash.XXH32: lambda data: xxhash.xxh32(data).digest(),
    Hash.XXH64: lambda data: xxhash.xxh64(data).digest(),
    Hash.XXH128: lambda data: xxhash.xxh128(data).digest(),
    Hash.SHA256: lambda data: hashlib.sha256(data).digest(),
    Hash.MD5: lambda data: hashlib.md5(data).digest(),  # noqa: S324
    Hash.SHA1: lambda data: hashlib.sha1(data).digest(),  # noqa: S324
    Hash.BLAKE2B: lambda data: hashlib.blake2b(data).digest(),
    Hash.BLAKE2S: lambda data: hashlib.blake2s(data).digest(),
}


@pytest.mark.parametrize("algorithm", list(Hash))
def test_digest_matches_reference(algorithm: Hash) -> None:
    digest = Data(PAYLOAD).digest(algorithm)
    assert isinstance(digest, Data)
    assert bytes(digest) == REFERENCES[algorithm](PAYLOAD)


def test_digest_accepts_algorithm_name() -> None:
    assert Data(PAYLOAD).digest("sha256") == Data(PAYLOAD).digest(Hash.SHA256)


@pytest.mark.parametrize("payload", [b"", PAYLOAD * 10000])
def test_digest_of_edge_sized_payloads(payload: bytes) -> None:
    assert bytes(Data(payload).digest("sha256")) == hashlib.sha256(payload).digest()


def test_digest_unknown_algorithm() -> None:
    with pytest.raises(ValueError, match="nosuchhash"):
        Data(PAYLOAD).digest("nosuchhash")
