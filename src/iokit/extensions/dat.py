__all__ = ["Dat"]

from typing import Any

from iokit.state import State


class Dat(State, suffix="dat"):
    def __init__(self, blob: bytes, **kwargs: Any):
        super().__init__(data=blob, **kwargs)

    def load(self) -> bytes:
        return self.data
