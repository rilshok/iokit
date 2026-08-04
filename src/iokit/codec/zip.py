__all__ = ["ZipCodec"]

from collections.abc import Iterable
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from typing import BinaryIO
from zipfile import ZipFile

from iokit.codec.base import Codec
from iokit.state import BufferedState, LoadedState, State
from iokit.utils.time import Timestamp


class ZipCodec(Codec[Iterable[State]]):
    def __init__(self, *, buffered: bool = False) -> None:
        self._buffered = buffered

    def __repr__(self) -> str:
        return f"{type(self).__name__}(buffered={self._buffered})"

    def encode(self, data: Iterable[State]) -> BytesIO:
        buffer = BytesIO()
        with ZipFile(buffer, mode="w") as archive:
            for state in data:
                archive.writestr(str(state.name), data=state.data)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Iterable[State]:
        with buffer, ZipFile(buffer, mode="r") as archive:
            for file in archive.namelist():
                info = archive.getinfo(file)
                if info.is_dir():
                    continue
                timestamp: Timestamp | None = None
                with suppress(ValueError):
                    timestamp = Timestamp.from_datetime(datetime(*info.date_time))
                with archive.open(file) as member_buffer:
                    if self._buffered:
                        yield BufferedState(buffer=member_buffer, key=file, timestamp=timestamp)
                    else:
                        yield LoadedState(data=member_buffer.read(), key=file, timestamp=timestamp)
