__all__ = ["CryptographyCodec", "decrypt", "encrypt"]

from hashlib import sha256
from io import BytesIO
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.base import Cipher
from cryptography.hazmat.primitives.ciphers.modes import GCM
from cryptography.hazmat.primitives.padding import PKCS7

from iokit.codec.base import Codec


def _to_bytes(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    return data.encode("utf-8")


def _get_hash(data: bytes) -> bytes:
    hasher = sha256()
    hasher.update(data)
    return hasher.digest()


def _generate_key(password: bytes, salt: bytes) -> bytes:
    password += salt
    for _ in range(390_000):
        password = _get_hash(password)
    return password


def _cipher(key: bytes, salt: bytes) -> Cipher[GCM]:
    return Cipher(algorithm=AES(key), mode=GCM(_get_hash(salt)))


def encrypt(data: bytes, password: bytes, salt: bytes) -> bytes:
    key = _generate_key(password=password, salt=salt)
    padder = PKCS7(128).padder()
    encryptor = _cipher(key=key, salt=salt).encryptor()
    padded = padder.update(data) + padder.finalize()
    ct = encryptor.update(padded) + encryptor.finalize()
    tag = encryptor.tag
    return ct + tag


def decrypt(data: bytes, password: bytes, salt: bytes) -> bytes:
    key = _generate_key(password=password, salt=salt)
    unpadder = PKCS7(128).unpadder()
    decryptor = _cipher(key=key, salt=salt).decryptor()
    ct, tag = data[:-16], data[-16:]
    try:
        padded = decryptor.update(ct) + decryptor.finalize_with_tag(tag)
    except InvalidTag as exc:
        msg = "Decryption failed"
        raise ValueError(msg) from exc
    return unpadder.update(padded) + unpadder.finalize()


_MASK = "..."


class CryptographyCodec(Codec[bytes]):
    """Raw bytes under AES-GCM, and back."""

    def __init__(self, password: bytes | str = "", salt: bytes | str = "") -> None:
        self._password = _to_bytes(password)
        self._salt = _to_bytes(salt)

    def __repr__(self) -> str:
        # a mask hides both the secret and its length
        password = _MASK if self._password else ""
        salt = _MASK if self._salt else ""
        return f"{type(self).__name__}({password=!r}, {salt=!r})"

    def encode(self, data: bytes) -> BytesIO:
        return BytesIO(encrypt(data=data, password=self._password, salt=self._salt))

    def decode(self, buffer: BinaryIO) -> bytes:
        with buffer:
            return decrypt(data=buffer.read(), password=self._password, salt=self._salt)
