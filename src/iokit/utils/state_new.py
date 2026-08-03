from collections.abc import Iterable
from fnmatch import fnmatch
from io import SEEK_END, SEEK_SET, BufferedReader, BytesIO, RawIOBase
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Generic, TypeVar

from .time import Timestamp

if TYPE_CHECKING:
    from _typeshed import WriteableBuffer

T = TypeVar("T", bound=object)


class Pattern(str):
    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(name=string, pat=str(self))


class Codec(Generic[T]):
    keys: str | Iterable[str]

    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError

    @classmethod
    def best_codec(cls, name: str) -> type["Codec[Any]"]:
        name = name.lower()
        scores: dict[type[Codec[Any]], int] = {}
        stack: list[type[Codec[Any]]] = [cls]
        seen: set[type[Codec[Any]]] = set()
        while stack:
            kls = stack.pop()
            if kls in seen:
                continue
            seen.add(kls)
            stack.extend(kls.__subclasses__())
            keys = getattr(kls, "keys", ())
            if isinstance(keys, str):
                keys = (keys,)
            for key in keys:
                pattern = Pattern(key.lower())
                if pattern(name):
                    scores[kls] = max(scores.get(kls, 0), len(pattern))
        return max(scores, key=scores.__getitem__)


class BytesCodec(Codec[bytes]):
    keys = "*"

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

    def load(self, codec: Codec[T] | None = None, **kwargs: object) -> T:
        if codec is None:
            engine_cls = Codec.best_codec(self.name)
            codec = engine_cls(**kwargs)
        elif kwargs:
            msg = "Cannot pass both engine instance and keyword arguments"
            raise ValueError(msg)
        with self.buffer as buffer:
            return codec.decode(buffer)


class _StreamView(RawIOBase):
    """Independent read cursor over a shared seekable stream. Closing it spares the source."""

    def __init__(self, source: BinaryIO) -> None:
        super().__init__()
        self._source = source
        self._position = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = SEEK_SET) -> int:
        self._source.seek(self._position)
        self._position = self._source.seek(offset, whence)
        return self._position

    def readinto(self, buffer: "WriteableBuffer") -> int:
        view = memoryview(buffer).cast("B")
        self._source.seek(self._position)
        chunk = self._source.read(view.nbytes)
        view[: len(chunk)] = chunk
        self._position += len(chunk)
        return len(chunk)


class BufferedState(State):
    def __init__(self, buffer: BinaryIO, key: str, timestamp: int | None = None) -> None:
        super().__init__(key=key, timestamp=timestamp)
        if not buffer.readable():
            msg = "Buffer must be readable"
            raise ValueError(msg)
        if not buffer.seekable():
            msg = "Buffer must be seekable"
            raise ValueError(msg)
        self._source = buffer

    @property
    def buffer(self) -> BufferedReader:
        return BufferedReader(_StreamView(self._source))

    @property
    def size(self) -> int:
        return self._source.seek(0, SEEK_END)


class LoadedState(State):
    def __init__(self, data: bytes, key: str, timestamp: int | None = None) -> None:
        super().__init__(key=key, timestamp=timestamp)
        self._data = data

    @property
    def data(self) -> Data:
        return Data(self._data)
