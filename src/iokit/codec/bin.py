"""Codec for raw bytes (no transformation)."""

from io import BytesIO
from typing import BinaryIO

from .base import Codec


class BinCodec(Codec[bytes]):
    """Convert between bytes and binary I/O without transformation."""

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}()"

    def encode(self, data: bytes) -> BinaryIO:
        """Wrap `data` in a binary buffer."""
        return BytesIO(data)

    def decode(self, buffer: BinaryIO) -> bytes:
        """Read all bytes from `buffer`."""
        return buffer.read()
