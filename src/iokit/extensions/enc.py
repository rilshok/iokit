__all__ = ["Enc", "SecretState", "decrypt", "encrypt"]

import struct
from collections.abc import Iterator
from datetime import datetime
from hashlib import sha256

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.base import Cipher
from cryptography.hazmat.primitives.ciphers.modes import GCM
from cryptography.hazmat.primitives.padding import PKCS7
from typing_extensions import Self

from iokit.state import State, StateName

DEFAULT_SALT = b"170309"


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
    def __init__(self, data: bytes) -> None:
        self.data = data

    def load(self, password: bytes | str, salt: bytes | str = DEFAULT_SALT) -> State:
        payload = decrypt(data=self.data, password=_to_bytes(password), salt=_to_bytes(salt))
        name, data = _unpack_arrays(payload)
        return State(data, name=name.decode("utf-8")).cast()

    def __repr__(self) -> str:
        return f"<SecretState: {len(self.data)} bytes>"

    @classmethod
    def pack(cls, state: State, password: bytes | str, salt: bytes | str = DEFAULT_SALT) -> Self:
        payload = _pack_arrays(str(state.name).encode("utf-8"), state.data)
        data = encrypt(data=payload, password=_to_bytes(password), salt=_to_bytes(salt))
        return cls(data=data)


class Enc(State, suffix="enc"):
    def __init__(
        self,
        data: State | SecretState,
        /,
        name: str | StateName = "",
        *,
        password: bytes | str | None = None,
        salt: bytes | str = DEFAULT_SALT,
        time: datetime | None = None,
    ) -> None:
        if isinstance(data, SecretState):
            if password is not None:
                msg = "Cannot encrypt already encrypted content."
                raise ValueError(msg)
            super().__init__(data.data, name=name or "", time=time)
            return

        if password is None:
            msg = "Password is required for encryption."
            raise ValueError(msg)
        super().__init__(
            SecretState.pack(state=data, password=password, salt=salt).data,
            name=name or str(data.name),
            time=time,
        )
        return

    def load(self) -> SecretState:
        return SecretState(data=self.data)
