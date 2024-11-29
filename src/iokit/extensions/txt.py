__all__ = ["Txt"]

from typing import Any

from iokit.state import State


class Txt(State, suffix="txt"):
    def __init__(self, content: str, /, **kwargs: Any):
        super().__init__(content.encode("utf-8"), **kwargs)

    def load(self) -> str:
        return self.data.decode("utf-8")
