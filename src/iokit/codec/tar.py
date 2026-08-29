"""Codec for TAR archives containing typed states."""

__all__ = ["TarCodec"]

import tarfile
from collections.abc import Iterable
from io import BytesIO
from typing import Any, BinaryIO

from iokit.codec.base import Codec
from iokit.state import BufferedState, LoadedState, State


class TarCodec(Codec[Iterable[State[Any]]]):
    """Pack states into TAR archives."""

    def __init__(self, *, buffered: bool = False) -> None:
        """Initialize with buffering mode.

        Args:
            buffered: Stream as `BufferedState` or load into memory.

        """
        self._buffered = buffered

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}(buffered={self._buffered})"

    def encode(self, data: Iterable[State[Any]]) -> BytesIO:
        """Pack states to TAR with paths and timestamps."""
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            for state in data:
                info = tarfile.TarInfo(name=state.path)
                info.size = state.size
                info.mtime = int(state.timestamp)
                archive.addfile(tarinfo=info, fileobj=state.buffer)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Iterable[State[Any]]:
        """Yield states from a TAR archive, optionally buffering member content."""
        with buffer, tarfile.open(fileobj=buffer, mode="r") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_buffer = archive.extractfile(member)
                if member_buffer is None:
                    continue
                with member_buffer:
                    if self._buffered:
                        yield BufferedState(
                            buffer=member_buffer,
                            path=member.name,
                            timestamp=member.mtime,
                        )
                    else:
                        yield LoadedState(
                            data=member_buffer.read(),
                            path=member.name,
                            timestamp=member.mtime,
                        )
