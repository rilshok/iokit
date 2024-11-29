__all__ = [
    "Dat",
]

from typing import Any

from iokit.state import State


class Dat(State, suffix="dat"):
    def __init__(self, data: bytes, **kwargs: Any):
        super().__init__(data=data, **kwargs)

    def load(self) -> bytes:
        return self._data.getvalue()
