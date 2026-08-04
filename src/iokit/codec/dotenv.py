__all__ = ["DotenvCodec"]


from io import BytesIO, TextIOWrapper
from typing import BinaryIO

from dotenv import dotenv_values

from iokit.codec.base import Codec

D = dict[str, str | None]


class DotenvCodec(Codec[D]):
    def __init__(self, encoding: str = "utf-8", *, interpolate: bool = False) -> None:
        self._encoding = encoding
        self._interpolate = interpolate

    def __repr__(self) -> str:
        return f"{type(self).__name__}(encoding={self._encoding}, interpolate={self._interpolate})"

    def _parse(self, buffer: BinaryIO, *, interpolate: bool) -> D:
        with buffer, TextIOWrapper(buffer, encoding=self._encoding, newline="") as stream:
            return dict(dotenv_values(stream=stream, interpolate=interpolate))

    def encode(self, data: D) -> BytesIO:
        buffer = BytesIO()
        for key, value in data.items():
            if value is None:
                line = f"{key}\n"
            else:
                # Single quotes keep the value literal; dotenv unescapes only \\ and \' there.
                escaped = value.replace("\\", "\\\\").replace("'", "\\'")
                line = f"{key}='{escaped}'\n"
            buffer.write(line.encode(self._encoding))
        # dotenv's grammar cannot express every string, so let its own parser vouch for the
        # result instead of silently emitting a file that reads back as different data.
        if self._parse(BytesIO(buffer.getvalue()), interpolate=False) != data:
            msg = "Dotenv data is not representable: it does not survive a decode round-trip"
            raise ValueError(msg)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> D:
        return self._parse(buffer, interpolate=self._interpolate)
