"""Codec for text with configurable character encoding."""

__all__ = ["TextCodec"]


from io import BytesIO
from typing import BinaryIO

from iokit.codec.base import Codec


class TextCodec(Codec[str]):
    """Encode text with specified character encoding."""

    def __init__(self, encoding: str = "utf-8") -> None:
        """Initialize codec with `encoding`.

        Args:
            encoding: Character encoding; defaults to 'utf-8'.

        """
        self._encoding = encoding

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}(encoding={self._encoding})"

    def encode(self, data: str) -> BytesIO:
        """Encode text to bytes."""
        return BytesIO(data.encode(self._encoding))

    def decode(self, buffer: BinaryIO) -> str:
        """Decode `buffer` bytes to text using the configured encoding."""
        with buffer:
            return buffer.read().decode(self._encoding)
