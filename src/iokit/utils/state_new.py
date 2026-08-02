from fnmatch import fnmatch
from io import BytesIO
from typing import BinaryIO, Generic, TypeVar

from .time import Timestamp

T = TypeVar("T", bound=object)


class Name(str):
    pass


class Pattern(str):
    def __call__(self, string: str) -> bool:
        return fnmatch(string, self)

    def __len__(self) -> int:
        return len(self.replace("*", ""))


class State:
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
    def size(self) -> int:
        return len(self.data)

    @property
    def data(self) -> bytes:
        with self.buffer as buffer:
            return buffer.read()

    @property
    def buffer(self) -> BinaryIO:
        return BytesIO(self.data)


class Engine(Generic[T]):
    names: tuple[Pattern, ...]

    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError
