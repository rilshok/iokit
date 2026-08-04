from io import SEEK_END, SEEK_SET, BufferedReader, BytesIO, RawIOBase
from os.path import relpath as _relpath
from pathlib import Path, PurePath
from types import UnionType
from typing import TYPE_CHECKING, Any, BinaryIO, Generic, Self, TypeVar

from humanize import naturalsize

from iokit.codec.base import Codec, Pattern, best_codec

from .time import Timestamp

if TYPE_CHECKING:
    from _typeshed import WriteableBuffer

T = TypeVar("T", bound=object)


class Data(bytes):
    pass


class State(Generic[T]):
    def __init__(self, key: str, timestamp: float | None = None) -> None:
        self.key = key
        self._timestamp = Timestamp.now() if timestamp is None else Timestamp(timestamp)

    def __repr__(self) -> str:
        size = naturalsize(self.size, gnu=True)
        return f"{self.key} ({size})"

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: float | None) -> None:
        self._timestamp = Timestamp.now() if value is None else Timestamp(value)

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = str(value)

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

    def _load(
        self,
        expected_type: type[T] | UnionType | None = None,
        *,
        codec: Codec[T] | None = None,
        **config: object,
    ) -> T:
        if codec is None:
            codec = best_codec(self.name, **config)
        elif config:
            msg = "Cannot pass both engine instance and keyword arguments"
            raise ValueError(msg)
        data = codec.decode(self.buffer)
        if expected_type is not None and not isinstance(data, expected_type):
            expectation = getattr(expected_type, "__name__", str(expected_type))
            msg = f"Expected loaded data of type '{expectation}', got '{type(data).__name__}'"
            raise TypeError(msg)
        return data

    def load(self, **config: object) -> T:
        return self._load(expected_type=None, codec=None, **config)

    @property
    def copy(self) -> "State[T]":
        return LoadedState(
            data=self.data,
            key=self.key,
            timestamp=self.timestamp,
        )


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


class BufferedState(State[T]):
    def __init__(self, buffer: BinaryIO, key: str, timestamp: float | None = None) -> None:
        self._source = buffer
        super().__init__(key=key, timestamp=timestamp)
        if not buffer.readable():
            msg = "Buffer must be readable"
            raise ValueError(msg)
        if not buffer.seekable():
            msg = "Buffer must be seekable"
            raise ValueError(msg)

    def __del__(self) -> None:
        self._source.close()

    @property
    def buffer(self) -> BufferedReader:
        return BufferedReader(_StreamView(self._source))

    @property
    def size(self) -> int:
        return self._source.seek(0, SEEK_END)


class FileState(State[T]):
    def __init__(
        self,
        path: str | Path,
        *,
        key_is_relpath: bool = True,
    ) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            msg = "Path is not a regular file"
            raise FileNotFoundError(msg)
        if key_is_relpath:
            key = PurePath(_relpath(self.path, Path.cwd())).as_posix()
        else:
            key = self.path.as_posix()
        timestamp = self.path.stat().st_mtime
        super().__init__(key=key, timestamp=timestamp)

    @property
    def buffer(self) -> BufferedReader:
        return self.path.open("rb")

    @property
    def size(self) -> int:
        return self.path.stat().st_size


class LoadedState(State[T]):
    def __init__(self, data: bytes, key: str, timestamp: float | None = None) -> None:
        super().__init__(key=key, timestamp=timestamp)
        self._data = data

    @property
    def data(self) -> Data:
        return Data(self._data)


V = TypeVar("V", bound=object)


class FormatState(LoadedState[T]):
    __patterns__: tuple[str | Pattern, ...]
    __expected__: type[T] | None = None

    def __init__(self, data: T | Data, key: str, timestamp: float | None = None) -> None:
        if not any(Pattern(p)(key) for p in self.__patterns__):
            msg = ""
            raise ValueError(msg)
        if isinstance(data, Data):
            super().__init__(data=data, key=key, timestamp=timestamp)
        else:
            with best_codec(key).encode(data) as content:
                super().__init__(data=content.read(), key=key, timestamp=timestamp)

    @classmethod
    def from_state(cls, state: State[Any]) -> Self:
        return cls(data=state.data, key=state.key, timestamp=state.timestamp)

    def load(self, **config: object) -> T:
        return self._load(expected_type=self.__expected__, codec=None, **config)

    @property
    def copy(self) -> State[T]:
        return type(self)(
            data=self.load(),
            key=self.key,
            timestamp=self.timestamp,
        )
