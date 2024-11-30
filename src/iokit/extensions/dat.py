__all__ = ["Dat"]


from datetime import datetime

from iokit.state import State, StateName


class Dat(State, suffix="dat"):
    def __init__(
        self,
        data: bytes,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        super().__init__(data, name=name, time=time)

    def load(self) -> bytes:
        return self.data
