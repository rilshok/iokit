from base64 import (
    b32decode,
    b32encode,
    b64decode,
    b64encode,
    urlsafe_b64decode,
    urlsafe_b64encode,
)
from collections.abc import Buffer
from os import urandom
from typing import (
    Literal,
    Self,
    SupportsIndex,
    overload,
)


class Data(bytes):
    @classmethod
    def from_ascii(cls, string: str) -> Self:
        return cls(string.encode("ascii"))

    @classmethod
    def from_int(
        cls,
        value: int,
        length: SupportsIndex = 1,
        byteorder: Literal["little", "big"] = "big",
    ) -> Self:
        return cls(value.to_bytes(length, byteorder))

    def to_int(self, byteorder: Literal["little", "big"] = "big") -> int:
        return int.from_bytes(self, byteorder)

    @classmethod
    def random(cls, nbytes: int) -> Self:
        return cls(urandom(nbytes))

    @classmethod
    def from_base64(cls, string: str) -> Self:
        return cls(b64decode(string))

    @property
    def base64(self) -> str:
        return b64encode(self).decode("ascii")

    @classmethod
    def from_base64url(cls, string: str) -> Self:
        padding = "=" * (-len(string) % 4)
        return cls(urlsafe_b64decode(string + padding))

    @property
    def base64url(self) -> str:
        return urlsafe_b64encode(self).decode("ascii").rstrip("=")

    def __add__(self, other: Buffer) -> "Data":
        return Data(super().__add__(other))

    def __mul__(self, other: SupportsIndex) -> "Data":
        return Data(super().__mul__(other))

    def __rmul__(self, other: SupportsIndex) -> "Data":
        return Data(super().__rmul__(other))

    @overload
    def __getitem__(self, key: int | SupportsIndex) -> int: ...

    @overload
    def __getitem__(self, key: slice) -> "Data": ...

    def __getitem__(self, key: int | slice | SupportsIndex) -> "Data | int":
        result = super().__getitem__(key)
        return result if isinstance(result, int) else Data(result)

    @property
    def base32crockford(self) -> str:
        # source: https://www.crockford.com/base32.html
        return "".join(
            chr(_BASE32_CROCKFORD_ENCODE_ALPHABET[_BASE32_RFC4648_DECODE_ALPHABET[ch]])
            for ch in b32encode(self).rstrip(b"=")
        )

    @classmethod
    def from_base32crockford(cls, string: str) -> Self:
        raw = "".join(
            chr(_BASE32_RFC4648_ENCODE_ALPHABET[_BASE32_CROCKFORD_DECODE_ALPHABET[ch]])
            for ch in string.encode()
        ).encode("ascii")
        pad_len = (-len(raw)) % 8
        raw += b"=" * pad_len
        return cls(b32decode(raw))


_BASE32_CROCKFORD_ENCODE_ALPHABET = dict(enumerate(b"0123456789ABCDEFGHJKMNPQRSTVWXYZ"))
_BASE32_CROCKFORD_DECODE_ALPHABET = {
    **dict.fromkeys(b"0Oo", 0),
    **dict.fromkeys(b"1IiLl", 1),
    **{48 + i: i for i in range(2, 10)},
    **{ch: i for i, ch in enumerate(b"abcdefghjkmnpqrstvwxyz", 10)},
    **{ch: i for i, ch in enumerate(b"ABCDEFGHJKMNPQRSTVWXYZ", 10)},
}

_BASE32_RFC4648_ENCODE_ALPHABET = dict(enumerate(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"))
_BASE32_RFC4648_DECODE_ALPHABET = {ch: i for i, ch in _BASE32_RFC4648_ENCODE_ALPHABET.items()}
