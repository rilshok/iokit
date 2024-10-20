import struct
from hashlib import sha256
from typing import Any, Iterator

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.base import Cipher
from cryptography.hazmat.primitives.ciphers.modes import GCM
from cryptography.hazmat.primitives.padding import PKCS7
from typing_extensions import Self

from iokit.state import State


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
    padded = decryptor.update(ct) + decryptor.finalize_with_tag(tag)
    return unpadder.update(padded) + unpadder.finalize()


def _pack_arrays(*arrays: bytes) -> bytes:
    packed_data = b""
    for arr in arrays:
        packed_data += struct.pack("!Q", len(arr)) + arr
    return packed_data


def _unpack_arrays(packed_data: bytes) -> Iterator[bytes]:
    while packed_data:
        length = struct.unpack("!Q", packed_data[:8])[0]
        packed_data = packed_data[8:]
        yield packed_data[:length]
        packed_data = packed_data[length:]


class SecretState:
    def __init__(self, data: bytes):
        self.data = data

    def load(self, password: bytes | str, salt: bytes | str = b"42") -> State:
        payload = decrypt(data=self.data, password=_to_bytes(password), salt=_to_bytes(salt))
        name, data = _unpack_arrays(payload)
        return State(data=data, name=name.decode("utf-8")).cast()

    def __repr__(self) -> str:
        return f"<SecretState: {len(self.data)} bytes>"

    @classmethod
    def pack(cls, state: State, password: bytes | str, salt: bytes | str = b"42") -> Self:
        payload = _pack_arrays(str(state.name).encode("utf-8"), state.data.getvalue())
        data = encrypt(data=payload, password=_to_bytes(password), salt=_to_bytes(salt))
        return cls(data=data)


class Encryption(State, suffix="enc"):
    def __init__(
        self,
        state: State,
        *,
        password: bytes | str,
        name: str | None = None,
        salt: bytes | str = b"170309",
        **kwargs: Any,
    ):
        if name is None:
            name = str(state.name)
        data = SecretState.pack(state=state, password=password, salt=salt).data
        super().__init__(data=data, name=name, **kwargs)

    def load(self) -> SecretState:
        return SecretState(data=self.data.getvalue())
