__all__ = ["Tar"]

import tarfile
from collections.abc import Iterable, Iterator
from datetime import datetime
from io import BytesIO

from iokit.state import State, StateName
from iokit.tools.time import fromtimestamp


class Tar(State, suffix="tar"):
    def __init__(
        self,
        data: Iterable[State],
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            with tarfile.open(fileobj=buffer, mode="w") as tar_buffer:
                for state in data:
                    file_data = tarfile.TarInfo(name=str(state.name))
                    file_data.size = state.size
                    file_data.mtime = int(state.time.timestamp())
                    tar_buffer.addfile(fileobj=state.buffer, tarinfo=file_data)

            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> Iterator[State]:
        with tarfile.open(fileobj=self.buffer, mode="r") as tar_buffer:
            for member in tar_buffer.getmembers():
                if not member.isfile():
                    continue
                member_buffer = tar_buffer.extractfile(member)
                if member_buffer is None:
                    continue
                yield State(
                    member_buffer.read(),
                    name=member.name,
                    time=fromtimestamp(member.mtime),
                )
