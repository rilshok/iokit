__all__ = ["Zip"]

from collections.abc import Iterable, Iterator
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

from iokit.state import State, StateName


class Zip(State, suffix="zip"):
    def __init__(
        self,
        data: Iterable[State],
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            with ZipFile(buffer, mode="w") as archive:
                for state in data:
                    archive.writestr(str(state.name), data=state.data)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> Iterator[State]:
        with ZipFile(self.buffer, mode="r") as archive:
            for file in archive.namelist():
                info = archive.getinfo(file)
                if info.is_dir():
                    continue
                time: datetime | None = None
                with suppress(ValueError):
                    time = datetime(*info.date_time)
                with archive.open(file) as member_buffer:
                    yield State(member_buffer.read(), name=file, time=time).cast()
