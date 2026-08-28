"""The digest of a payload, checked against the library that names the algorithm.

`Data` is the bytes a state is made of, and a digest of it is bytes of the same kind, so a
checksum can be stored, compared or written out like any other payload.
"""

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
    Hash.XXH3_64: lambda data: xxhash.xxh3_64(data).digest(),
    Hash.XXH3_128: lambda data: xxhash.xxh3_128(data).digest(),
    Hash.MD5: lambda data: hashlib.md5(data).digest(),  # noqa: S324
    Hash.SHA1: lambda data: hashlib.sha1(data).digest(),  # noqa: S324
    Hash.SHA224: lambda data: hashlib.sha224(data).digest(),
    Hash.SHA256: lambda data: hashlib.sha256(data).digest(),
    Hash.SHA384: lambda data: hashlib.sha384(data).digest(),
    Hash.SHA512: lambda data: hashlib.sha512(data).digest(),
    Hash.SHA3_224: lambda data: hashlib.sha3_224(data).digest(),
    Hash.SHA3_256: lambda data: hashlib.sha3_256(data).digest(),
    Hash.SHA3_384: lambda data: hashlib.sha3_384(data).digest(),
    Hash.SHA3_512: lambda data: hashlib.sha3_512(data).digest(),
    Hash.BLAKE2B: lambda data: hashlib.blake2b(data).digest(),
    Hash.BLAKE2S: lambda data: hashlib.blake2s(data).digest(),
}


def test_every_algorithm_has_a_reference_to_be_checked_against() -> None:
    """Nothing is left untested by the table above quietly missing an entry."""
    assert set(REFERENCES) == set(Hash)


@pytest.mark.parametrize("algorithm", list(Hash))
def test_a_digest_is_the_one_the_algorithm_is_known_for(algorithm: Hash) -> None:
    digest = Data(PAYLOAD).digest(algorithm)
    assert isinstance(digest, Data)
    assert bytes(digest) == REFERENCES[algorithm](PAYLOAD)


def test_an_algorithm_may_be_named_instead_of_chosen() -> None:
    assert Data(PAYLOAD).digest("sha256") == Data(PAYLOAD).digest(Hash.SHA256)


@pytest.mark.parametrize("payload", [b"", PAYLOAD * 10000])
def test_a_payload_of_any_length_is_digested(payload: bytes) -> None:
    assert bytes(Data(payload).digest("sha256")) == hashlib.sha256(payload).digest()


def test_an_algorithm_of_no_such_name_is_refused() -> None:
    with pytest.raises(ValueError, match="nosuchhash"):
        Data(PAYLOAD).digest("nosuchhash")
