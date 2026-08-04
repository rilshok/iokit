__all__ = ["SecretState", "decrypt", "encrypt"]

import struct
from hashlib import sha256
from io import BytesIO
from typing import BinaryIO, Self

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.base import Cipher
from cryptography.hazmat.primitives.ciphers.modes import GCM
from cryptography.hazmat.primitives.padding import PKCS7

from iokit.codec.base import Codec
from iokit.state import LoadedState, State


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


_MAGIC = b"IOKS"
_VERSION = 1
_HEADER_FORMAT = "!4sBHd"
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)
_MAX_KEY_SIZE = 0xFFFF


def _pack_state(state: State) -> bytes:
    """Serialize a state into `header || key || data`.

    The header is a fixed 15-byte big-endian struct holding the magic, the format version,
    the key length and the timestamp. The payload is the remainder of the buffer, so its
    length needs no framing of its own.
    """
    key = state.key.encode("utf-8")
    if len(key) > _MAX_KEY_SIZE:
        msg = f"Key is too long to pack: {len(key)} bytes, maximum is {_MAX_KEY_SIZE}"
        raise ValueError(msg)
    header = struct.pack(_HEADER_FORMAT, _MAGIC, _VERSION, len(key), float(state.timestamp))
    return header + key + state.data


def _unpack_state(packed_data: bytes) -> LoadedState:
    if len(packed_data) < _HEADER_SIZE:
        msg = f"Packed state is truncated: expected at least {_HEADER_SIZE} bytes"
        raise ValueError(msg)
    header = packed_data[:_HEADER_SIZE]
    magic, version, key_size, timestamp = struct.unpack(_HEADER_FORMAT, header)
    if magic != _MAGIC:
        msg = "Packed state has an invalid signature"
        raise ValueError(msg)
    if version != _VERSION:
        msg = f"Unsupported packed state version: {version}, expected {_VERSION}"
        raise ValueError(msg)
    key_end = _HEADER_SIZE + key_size
    if len(packed_data) < key_end:
        msg = "Packed state is truncated: key does not fit into the buffer"
        raise ValueError(msg)
    key = packed_data[_HEADER_SIZE:key_end]
    data = packed_data[key_end:]
    return LoadedState(data, key=key.decode("utf-8"), timestamp=timestamp)


class SecretState:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def load(self, password: bytes | str, salt: bytes | str) -> LoadedState:
        payload = decrypt(data=self.data, password=_to_bytes(password), salt=_to_bytes(salt))
        return _unpack_state(payload)

    def __repr__(self) -> str:
        return f"<SecretState: {len(self.data)} bytes>"

    @classmethod
    def pack(cls, state: State, password: bytes | str, salt: bytes | str) -> Self:
        payload = _pack_state(state)
        data = encrypt(data=payload, password=_to_bytes(password), salt=_to_bytes(salt))
        return cls(data=data)


_MASK = "..."


class CryptographyCodec(Codec[State]):
    def __init__(self, password: bytes | str = "", salt: bytes | str = "") -> None:
        self._password = password
        self._salt = salt

    def __repr__(self) -> str:
        # a mask hides both the secret and its length
        password = _MASK if self._password else ""
        salt = _MASK if self._salt else ""
        return f"{type(self).__name__}({password=!r}, {salt=!r})"

    def encode(self, data: State) -> BytesIO:
        state = SecretState.pack(state=data, password=self._password, salt=self._salt)
        return BytesIO(state.data)

    def decode(self, buffer: BinaryIO) -> State:
        return SecretState(data=buffer.read()).load(password=self._password, salt=self._salt)
