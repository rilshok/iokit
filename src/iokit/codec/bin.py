from io import BytesIO
from typing import BinaryIO

from .base import Codec


class BinCodec(Codec[bytes]):
    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def encode(self, data: bytes) -> BinaryIO:
        return BytesIO(data)

    def decode(self, buffer: BinaryIO) -> bytes:
        return buffer.read()
