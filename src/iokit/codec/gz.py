__all__ = ["GzipCodec"]

import gzip
from io import BytesIO
from typing import BinaryIO

from iokit.codec.base import Codec


class GzipCodec(Codec[bytes]):
    """Raw bytes in a gzip stream, and back."""

    def __init__(self, compression: int = 1) -> None:
        self._compression = compression

    def __repr__(self) -> str:
        return f"{type(self).__name__}(compression={self._compression})"

    def encode(self, data: bytes) -> BytesIO:
        buffer = BytesIO()
        # a fixed modification time keeps the same bytes
        gzip_file = gzip.GzipFile(
            fileobj=buffer,
            mode="wb",
            compresslevel=self._compression,
            mtime=0,
        )
        with gzip_file as gzip_buffer:
            gzip_buffer.write(data)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> bytes:
        with buffer, gzip.GzipFile(fileobj=buffer, mode="rb") as gzip_buffer:
            return gzip_buffer.read()
