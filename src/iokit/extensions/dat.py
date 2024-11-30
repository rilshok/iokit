__all__ = ["Dat"]


from datetime import datetime

from iokit.state import State, StateName


class Dat(State, suffix="dat"):
    def __init__(
        self,
        content: bytes,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        super().__init__(content, name=name, time=time)

    def load(self) -> bytes:
        return self.data
