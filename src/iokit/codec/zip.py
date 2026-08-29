__all__ = ["ZipCodec"]

from collections.abc import Iterable
from contextlib import suppress
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, BinaryIO
from zipfile import ZipFile, ZipInfo

from iokit.codec.base import Codec
from iokit.state import BufferedState, LoadedState, State
from iokit.utils.time import Timestamp


class ZipCodec(Codec[Iterable[State[Any]]]):
    def __init__(self, *, buffered: bool = False) -> None:
        self._buffered = buffered

    def __repr__(self) -> str:
        return f"{type(self).__name__}(buffered={self._buffered})"

    def encode(self, data: Iterable[State[Any]]) -> BytesIO:
        buffer = BytesIO()
        with ZipFile(buffer, mode="w") as archive:
            for state in data:
                # the whole path, and the local time a zip keeps its members by
                touched = state.timestamp.datetime.astimezone().timetuple()
                archive.writestr(ZipInfo(state.path, touched[:6]), data=state.data)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Iterable[State[Any]]:
        with buffer, ZipFile(buffer, mode="r") as archive:
            for file in archive.namelist():
                info = archive.getinfo(file)
                if info.is_dir():
                    continue
                timestamp: Timestamp | None = None
                with suppress(ValueError):
                    # a zip keeps a bare wall clock, so read it back as local time
                    touched = datetime(*info.date_time, tzinfo=timezone.utc).replace(tzinfo=None)
                    timestamp = Timestamp.from_datetime(touched.astimezone())
                with archive.open(file) as member_buffer:
                    if self._buffered:
                        yield BufferedState(buffer=member_buffer, path=file, timestamp=timestamp)
                    else:
                        yield LoadedState(data=member_buffer.read(), path=file, timestamp=timestamp)
