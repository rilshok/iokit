"""`Data`, the bytes a state is made of: a `bytes` that slices, spells and digests into more
of itself.
"""

import hashlib
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

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


@pytest.mark.parametrize(
    ("payload", "base64", "base64url", "crockford"),
    [
        (b"", "", "", ""),
        (b"iokit", "aW9raXQ=", "aW9raXQ", "D5QPPTBM"),
        # the bytes base64 spells with the two characters a url would take for its own
        (b"\xfb\xef\xbe", "++++", "----", "ZFQVW"),
    ],
    ids=["empty", "text", "url unsafe"],
)
def test_data_spells_itself_out_and_is_read_back_from_the_spelling(
    payload: bytes,
    base64: str,
    base64url: str,
    crockford: str,
) -> None:
    """Each spelling is a round trip: what `Data` writes reads back as the bytes it came from."""
    data = Data(payload)
    assert (data.base64, data.base64url, data.base32crockford) == (base64, base64url, crockford)
    assert Data.from_base64(base64) == payload
    assert Data.from_base64url(base64url) == payload
    assert Data.from_base32crockford(crockford) == payload


def test_data_is_made_of_the_pieces_it_is_built_from() -> None:
    """Whatever is done to `Data` gives `Data` back, so the reach of it is never lost."""
    data = Data.from_ascii("iokit")
    assert data + b"!" == b"iokit!"
    assert data[:2] == b"io"
    assert data[0] == ord("i")
    assert data * 2 == b"iokitiokit"
    assert 2 * data == b"iokitiokit"
    for piece in (data + b"!", data[:2], data * 2, 2 * data):
        assert isinstance(piece, Data)


def test_data_carries_a_number_of_a_width_it_is_told() -> None:
    assert Data.from_int(1_000, length=2) == b"\x03\xe8"
    assert Data.from_int(1_000, length=2).to_int() == 1_000
    assert Data.from_int(1_000, length=2, byteorder="little").to_int(byteorder="little") == 1_000


def test_random_data_is_of_the_length_that_was_asked_for() -> None:
    assert len(Data.random(16)) == 16
    assert Data.random(16) != Data.random(16)


def test_a_digest_is_the_same_however_the_payload_is_reached(tmp_path: Path) -> None:
    """Bytes, an open buffer or a file on disk digest alike, the file read in chunks."""
    path = tmp_path / "payload.bin"
    path.write_bytes(PAYLOAD)
    expected = Data(PAYLOAD).digest("sha256")
    with BytesIO(PAYLOAD) as buffer:
        assert Data.digest_from_io("sha256", buffer) == expected
    assert Data.digest_from_path(path, "sha256") == expected
    assert Data.digest_from_path(path, "sha256", chunk_size=1) == expected
