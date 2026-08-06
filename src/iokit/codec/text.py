__all__ = ["TextCodec"]


from io import BytesIO
from typing import BinaryIO

from iokit.codec.base import Codec


class TextCodec(Codec[str]):
    def __init__(self, encoding: str = "utf-8") -> None:
        self._encoding = encoding

    def __repr__(self) -> str:
        return f"{type(self).__name__}(encoding={self._encoding})"

    def encode(self, data: str) -> BytesIO:
        return BytesIO(data.encode(self._encoding))

    def decode(self, buffer: BinaryIO) -> str:
        with buffer:
            return buffer.read().decode(self._encoding)
