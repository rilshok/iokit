__all__ = ["Txt"]


from datetime import datetime

from iokit.state import State, StateName


class Txt(State, suffix="txt"):
    def __init__(
        self,
        content: str,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        super().__init__(content.encode("utf-8"), name=name, time=time)

    def load(self) -> str:
        return self.data.decode("utf-8")
