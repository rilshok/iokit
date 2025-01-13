__all__ = ["Zip"]

import zipfile
from collections.abc import Iterable, Iterator
from contextlib import suppress
from datetime import datetime
from io import BytesIO

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
            with zipfile.ZipFile(buffer, mode="w") as zip_buffer:
                for state in data:
                    zip_buffer.writestr(str(state.name), data=state.data)

            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> Iterator[State]:
        with zipfile.ZipFile(self.buffer, mode="r") as zip_buffer:
            for file in zip_buffer.namelist():
                with zip_buffer.open(file) as member_buffer:
                    time: datetime | None = None
                    with suppress(ValueError):
                        time = datetime(*zip_buffer.getinfo(file).date_time)
                    yield State(member_buffer.read(), name=file, time=time)
