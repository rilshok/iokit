__all__ = ["GzipCodec"]

import gzip
from io import BytesIO
from shutil import copyfileobj
from typing import BinaryIO, TypeVar

from iokit.codec.base import Codec
from iokit.codec.bin import BinCodec

T = TypeVar("T", bound=object)


class GzipCodec(Codec[T]):
    """Wrap another codec into a gzip stream, or the raw bytes when there is none."""

    def __init__(self, codec: Codec[T] | None = None, compression: int = 1) -> None:
        self._codec: Codec[T] = BinCodec() if codec is None else codec  # type: ignore[assignment]
        self._compression = compression

    def __repr__(self) -> str:
        return f"{type(self).__name__}(codec={self._codec!r}, compression={self._compression})"

    def encode(self, data: T) -> BytesIO:
        buffer = BytesIO()
        gzip_file = gzip.GzipFile(
            fileobj=buffer,
            mode="wb",
            compresslevel=self._compression,
            mtime=0,
        )
        with self._codec.encode(data) as payload, gzip_file as gzip_buffer:
            copyfileobj(payload, gzip_buffer)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> T:
        with buffer, gzip.GzipFile(fileobj=buffer, mode="rb") as gzip_buffer:
            # The wrapped codec may need to seek, which a gzip stream does only by re-reading it.
            payload = BytesIO(gzip_buffer.read())
        return self._codec.decode(payload)
