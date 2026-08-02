from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Generic, TypeVar

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

    @classmethod
    def check_name(cls, name: str) -> bool:
        return any(pattern(name) for pattern in cls.keys)

    @classmethod
    def find_best_engine(cls, name: str) -> "type[Engine[Any]]":
        scores: dict[type[Engine[Any]], int] = {}
        for kls in cls.__subclasses__():
            for key in kls.keys:
                if key(name):
                    scores[kls] = max(scores.get(kls, 0), len(key))
        return max(scores, key=scores.__getitem__, default=BytesEngine)


class BytesEngine(Engine[bytes]):
    def encode(self, data: bytes) -> BinaryIO:
        return BytesIO(data)

    def decode(self, buffer: BinaryIO) -> bytes:
        return buffer.read()


class Data(bytes):
    pass


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
    def data(self) -> Data:
        with self.buffer as buffer:
            return Data(buffer.read())

    @property
    def buffer(self) -> BinaryIO:
        return BytesIO(self.data)

    def load(self, engine: Engine[T] | None) -> T:
        if engine is None:
            engine = Engine.find_best_engine(self.name)()
        with self.buffer as buffer:
            return engine.decode(buffer)
