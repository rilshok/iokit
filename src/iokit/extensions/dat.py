__all__ = ["Dat"]

from typing import Any

from iokit.state import State


class Dat(State, suffix="dat"):
    def __init__(self, content: bytes, /, **kwargs: Any) -> None:
        super().__init__(content, **kwargs)

    def load(self) -> bytes:
        return self.data
