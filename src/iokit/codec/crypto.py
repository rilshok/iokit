"""Codec for bytes encrypted with AES-GCM."""

__all__ = ["CryptographyCodec", "decrypt", "encrypt"]

from functools import lru_cache
from hashlib import pbkdf2_hmac
from io import BytesIO
from os import urandom
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from iokit.codec.base import Codec

#: the nonce size AES-GCM is specified for
_NONCE_SIZE = 12

#: what OWASP asks of PBKDF2-HMAC-SHA256, and what the loop it replaces already cost
_ITERATIONS = 600_000


def _to_bytes(data: bytes | str) -> bytes:
    """Convert `data` to bytes, encoding strings as UTF-8."""
    if isinstance(data, bytes):
        return data
    return data.encode("utf-8")


@lru_cache(maxsize=8)
def _generate_key(password: bytes, salt: bytes) -> bytes:
    """Derive key from `password` and `salt` using PBKDF2."""
    # the whole cost of sealing a record, and a storage seals every record under one password
    return pbkdf2_hmac("sha256", password, salt, _ITERATIONS, dklen=32)


def encrypt(data: bytes, password: bytes, salt: bytes) -> bytes:
    """Encrypt `data` with `password` and `salt`."""
    # a keystream is settled by the key and the nonce, and one used twice gives both away
    nonce = urandom(_NONCE_SIZE)
    return nonce + AESGCM(_generate_key(password, salt)).encrypt(nonce, data, None)


def decrypt(data: bytes, password: bytes, salt: bytes) -> bytes:
    """Decrypt `data` with `password` and `salt`."""
    nonce, sealed = data[:_NONCE_SIZE], data[_NONCE_SIZE:]
    try:
        return AESGCM(_generate_key(password, salt)).decrypt(nonce, sealed, None)
    except (InvalidTag, ValueError) as exc:
        # a record too short to hold a nonce and a tag is as unopenable as a meddled one
        msg = "Decryption failed"
        raise ValueError(msg) from exc


_MASK = "..."


class CryptographyCodec(Codec[bytes]):
    """Encrypt and decrypt bytes using AES-GCM."""

    def __init__(self, password: bytes | str = "", salt: bytes | str = "") -> None:
        """Initialize codec with `password` and `salt`.

        Args:
            password: Encryption password.
            salt: Key derivation salt.

        """
        self._password = _to_bytes(password)
        self._salt = _to_bytes(salt)

    def __repr__(self) -> str:
        """Return codec representation."""
        # a mask hides both the secret and its length
        password = _MASK if self._password else ""
        salt = _MASK if self._salt else ""
        return f"{type(self).__name__}({password=!r}, {salt=!r})"

    def encode(self, data: bytes) -> BytesIO:
        """Encrypt `data` and write to a buffer."""
        return BytesIO(encrypt(data=data, password=self._password, salt=self._salt))

    def decode(self, buffer: BinaryIO) -> bytes:
        """Decrypt `buffer` and return plaintext bytes."""
        with buffer:
            return decrypt(data=buffer.read(), password=self._password, salt=self._salt)
