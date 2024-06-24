__all__ = [
    "Dat",
]

from typing import Any

from iokit.state import Payload, State


class Dat(State, suffix="dat"):
    def __init__(self, data: Payload, **kwargs: Any):
        super().__init__(data=data, **kwargs)

    def load(self) -> bytes:
        return self._data.getvalue()
