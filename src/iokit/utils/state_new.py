from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Generic, TypeVar

from .time import Timestamp

T = TypeVar("T", bound=object)


class Pattern(str):
    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(string, self)


class Engine(Generic[T]):
    keys: tuple[Pattern, ...]

    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError


class State:
    def __init__(self, key: str, timestamp: int | None = None) -> None:
        self.key = key
        self._timestamp = Timestamp.now() if timestamp is None else Timestamp(timestamp)

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: int | None) -> None:
        self._timestamp = Timestamp.now() if value is None else Timestamp(value)

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        key = Path(value)
        if key.is_absolute():
            msg = "Key must be relative, not absolute"
            raise ValueError(msg)
        self._key = key.as_posix()

    @property
    def name(self) -> str:
        return Path(self._key).name

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

    def load(self, engine: Engine[T] | None) -> T:
        if engine is None:
            raise NotImplementedError
        with self.buffer as buffer:
            return engine.decode(buffer)
