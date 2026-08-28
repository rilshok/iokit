import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from iokit import Dat, Data
from iokit.utils.checksum import Hash

PAYLOAD = b"the quick brown fox jumps over the lazy dog"


@pytest.mark.parametrize("algorithm", list(Hash))
def test_digest_matches_stream_digest(algorithm: Hash) -> None:
    data = Data(PAYLOAD)
    assert data.digest(algorithm) == Data.digest_from_io(algorithm, BytesIO(data))


def test_digest_matches_hashlib() -> None:
    data = Data(PAYLOAD)
    assert bytes(data.digest("sha256")) == hashlib.sha256(PAYLOAD).digest()
    assert bytes(data.digest("blake2b")) == hashlib.blake2b(PAYLOAD).digest()


def test_digest_accepts_str_and_enum() -> None:
    data = Data(PAYLOAD)
    assert data.digest("xxh64") == data.digest(Hash.XXH64)


def test_digest_returns_data() -> None:
    digest = Data(PAYLOAD).digest("md5")
    assert isinstance(digest, Data)
    assert len(digest) == hashlib.md5(PAYLOAD).digest_size  # noqa: S324
    assert digest.base64


def test_digest_of_empty_data() -> None:
    assert bytes(Data(b"").digest("sha256")) == hashlib.sha256(b"").digest()


def test_digest_differs_for_different_data() -> None:
    assert Data(b"foo").digest("sha1") != Data(b"bar").digest("sha1")


def test_digest_unknown_algorithm() -> None:
    with pytest.raises(ValueError, match="nosuchhash"):
        Data(PAYLOAD).digest("nosuchhash")


def test_digest_matches_chunked_digest() -> None:
    payload = PAYLOAD * 1000
    chunked = Data.digest_from_io("sha256", BytesIO(payload), chunk_size=7)
    assert Data(payload).digest("sha256") == chunked


def test_digest_matches_file_digest(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(PAYLOAD)
    assert Data(PAYLOAD).digest("sha256") == Data.digest_from_path(path, "sha256")


def test_digest_matches_state_digest() -> None:
    state = Dat(PAYLOAD, path="payload.dat")
    assert state.data.digest("sha256") == state.digest("sha256")
