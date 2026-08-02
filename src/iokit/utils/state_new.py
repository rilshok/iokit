from abc import ABC, abstractmethod
from io import BytesIO
from typing import BinaryIO

from .time import Timestamp


class Name(str):
    pass


class State(ABC):
    def __init__(self, name: str, timestamp: int | None = None) -> None:
        self._name = Name(name)
        self._timestamp = Timestamp.now() if timestamp is None else Timestamp(timestamp)

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def name(self) -> Name:
        return self._name

    @property
    @abstractmethod
    def size(self) -> int:
        return len(self.data)

    @property
    def data(self) -> bytes:
        with self.buffer as buffer:
            return buffer.read()

    @property
    def buffer(self) -> BinaryIO:
        return BytesIO(self.data)
