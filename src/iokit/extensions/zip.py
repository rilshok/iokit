import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any, Iterable

from iokit.state import State


class Zip(State, suffix="zip"):
    def __init__(self, states: Iterable[State], **kwargs: Any):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w") as zip_buffer:
            for state in states:
                zip_buffer.writestr(str(state.name), data=state.data.getvalue())

        super().__init__(data=buffer, **kwargs)

    def load(self) -> list[State]:
        states: list[State] = []
        with zipfile.ZipFile(self.data, mode="r") as zip_buffer:
            for file in zip_buffer.namelist():
                with zip_buffer.open(file) as member_buffer:
                    state = State(
                        data=member_buffer.read(),
                        name=file,
                        time=datetime(*zip_buffer.getinfo(file).date_time),
                    )
                    states.append(state)
        return states
