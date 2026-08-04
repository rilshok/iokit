from collections.abc import Iterable
from importlib import import_module
from io import SEEK_END, SEEK_SET, BufferedReader, BytesIO, RawIOBase
from os.path import relpath as _relpath
from pathlib import Path, PurePath
from types import UnionType
from typing import TYPE_CHECKING, Any, BinaryIO, Generic, Self, TypeVar

from humanize import naturalsize

from iokit.codec.base import Codec, best_codec
from iokit.dtype.extension import Extension
from iokit.utils.time import Timestamp

if TYPE_CHECKING:
    from _typeshed import WriteableBuffer
    from numpy.typing import NDArray  # noqa: F401
    from pandas import DataFrame  # noqa: F401
    from PIL.Image import Image as PillowImage  # noqa: F401

    from iokit.dtype.waveform import Waveform  # noqa: F401


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
        if expected_type is None:
            return data
        if isinstance(expected_type, tuple) and len(expected_type) == 0:
            return data
        if isinstance(data, expected_type):
            return data
        expectation = getattr(expected_type, "__name__", str(expected_type))
        msg = f"Expected loaded data of type '{expectation}', got '{type(data).__name__}'"
        raise TypeError(msg)

    def load(self, **config: object) -> T:
        return self._load(expected_type=None, codec=None, **config)

    @property
    def copy(self) -> "State[T]":
        return LoadedState(
            data=self.data,
            key=self.key,
            timestamp=self.timestamp,
        )

    def gzip(self, *, compression: int = 1) -> "Gzip":
        """Compress this state as it stands.

        Args:
            compression: The gzip level, from 0 for none to 9 for the smallest output.

        Returns:
            The compressed state, keyed after this one with `.gz` appended.
        """
        return Gzip(self, compression=compression)

    def encrypt(self, *, password: bytes | str, salt: bytes | str = "") -> "Enc":
        """Encrypt this state, its key and timestamp packed in along with the payload.

        Args:
            password: The secret guarding the payload, to be repeated on loading.
            salt: Extra input to the key derivation, to be repeated on loading.

        Returns:
            The encrypted state, keyed after this one with `.enc` appended.
        """
        return Enc(
            self,
            key=self.key + Enc.extension(),
            timestamp=self.timestamp,
            password=password,
            salt=salt,
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


class FormatState(LoadedState[T]):
    __extension__: Extension
    # An unparameterized class, or a union of them, checked against the loaded payload.
    __expected__: "type[Any] | UnionType | None" = None

    def __init__(
        self,
        data: T | Data,
        key: str,
        timestamp: float | None = None,
        **config: object,
    ) -> None:
        self._assert_key(key)
        if isinstance(data, Data):
            if config:
                msg = "Cannot configure a codec for already encoded data"
                raise ValueError(msg)
            super().__init__(data=data, key=key, timestamp=timestamp)
        else:
            with best_codec(key, **config).encode(data) as content:
                super().__init__(data=content.read(), key=key, timestamp=timestamp)

    @classmethod
    def extension(cls) -> str:
        return cls.__extension__.value

    @classmethod
    def _assert_key(cls, key: str) -> None:
        if key.lower().endswith(cls.extension()):
            return
        msg = f"Key must end with {cls.extension()!r} extension"
        raise ValueError(msg)

    @classmethod
    def _expected(cls) -> "type[T] | UnionType | None":
        return cls.__expected__

    @classmethod
    def from_state(cls, state: State[Any]) -> Self:
        cls._assert_key(state.key)
        return cls(data=state.data, key=state.key, timestamp=state.timestamp)

    def load(self, **config: object) -> T:
        return self._load(expected_type=self._expected(), codec=None, **config)

    @property
    def copy(self) -> State[T]:
        return type(self)(
            data=self.load(),
            key=self.key,
            timestamp=self.timestamp,
        )


class LazyFormatState(FormatState[T]):
    """A format whose payload type comes from an optional dependency, imported only on load."""

    __expected_spec__: str  # "module:attribute"

    @classmethod
    def _expected(cls) -> "type[T]":
        module, _, attribute = cls.__expected_spec__.partition(":")
        return getattr(import_module(module), attribute)


class Dat(FormatState[bytes]):
    __extension__ = Extension.DAT
    __expected__ = bytes


class Bin(Dat):
    __extension__ = Extension.BIN


class Txt(FormatState[str]):
    __extension__ = Extension.TXT
    __expected__ = str


class Document(FormatState[dict[str, Any] | list[Any] | str]):
    """A structured document: a mapping, a sequence, or a bare scalar string."""

    __expected__ = dict | list | str


class Json(Document):
    __extension__ = Extension.JSON


class Jsonl(FormatState[list[dict[str, Any]]]):
    """JSON Lines: one record per line, so the payload is always a list of records."""

    __extension__ = Extension.JSONL
    __expected__ = list


class Yaml(Document):
    __extension__ = Extension.YAML


class Yml(Yaml):
    __extension__ = Extension.YML


class Env(FormatState[dict[str, str | None]]):
    """A dotenv file; a variable declared without a value loads as `None`."""

    __extension__ = Extension.ENV
    __expected__ = dict


class Npy(LazyFormatState["NDArray[Any]"]):
    __extension__ = Extension.NPY
    __expected_spec__ = "numpy:ndarray"


class Pandas(LazyFormatState["DataFrame"]):
    """A dataframe stored as delimited text."""

    __expected_spec__ = "pandas:DataFrame"


class Csv(Pandas):
    __extension__ = Extension.CSV


class Tsv(Pandas):
    __extension__ = Extension.TSV


class Image(LazyFormatState["PillowImage"]):
    """A raster image, decoded by Pillow."""

    __expected_spec__ = "PIL.Image:Image"


class Jpeg(Image):
    __extension__ = Extension.JPEG


class Jpg(Jpeg):
    __extension__ = Extension.JPG


class Png(Image):
    __extension__ = Extension.PNG


class Archive(FormatState[Iterable[State[Any]]]):
    """A container of whole states: loading one yields its members, lazily."""

    __expected__ = Iterable


class Zip(Archive):
    __extension__ = Extension.ZIP


class Tar(Archive):
    __extension__ = Extension.TAR


class Gzip(FormatState[Any]):
    """A gzip stream around another format: `data.json.gz` holds what `data.json` would.

    The wrapped format comes from the rest of the key, so the payload is whatever it decodes
    to, and a key with no other suffix, like `data.gz`, simply holds bytes. A whole state is
    compressed as it stands and takes its key along, gaining the suffix: `data.json` becomes
    `data.json.gz`, which still loads as the document it was.
    """

    __extension__ = Extension.GZ

    def __init__(
        self,
        data: Any,  # noqa: ANN401
        key: str | None = None,
        timestamp: float | None = None,
        **config: object,
    ) -> None:
        if isinstance(data, State):
            key = data.key + self.extension() if key is None else key
            timestamp = data.timestamp if timestamp is None else timestamp
            # The state carries encoded bytes already, so only the gzip layer is left to add,
            # which is what the suffix on its own resolves to.
            with best_codec(self.extension(), **config).encode(data.data) as content:
                super().__init__(Data(content.read()), key=key, timestamp=timestamp)
            return
        if key is None:
            msg = "Key is required for anything but a state"
            raise ValueError(msg)
        super().__init__(data, key=key, timestamp=timestamp, **config)


class Enc(FormatState[State[Any]]):
    """An encrypted state, key and timestamp included.

    The `password` and `salt` are given when encoding, and again when loading:
    `Enc(state, "secret.enc", password="...").load(password="...")`.
    """

    __extension__ = Extension.ENC
    __expected__ = State

    @property
    def copy(self) -> State[State[Any]]:
        # re-encrypting would ask for the password again, and yield different bytes anyway.
        return self.from_state(self)


A = TypeVar("A", bound="Audio")


class Audio(LazyFormatState["Waveform"]):
    __expected_spec__ = "iokit.dtype.waveform:Waveform"

    def _to_audio(self, kls: type[A]) -> A:
        self._assert_key(self.key)
        new_key = self.key.removesuffix(self.extension()) + kls.extension()
        return kls(data=self.load(), key=new_key, timestamp=self.timestamp)

    @property
    def flac(self) -> "Flac":
        return self._to_audio(Flac)

    @property
    def wav(self) -> "Wav":
        return self._to_audio(Wav)

    @property
    def mp3(self) -> "Mp3":
        return self._to_audio(Mp3)

    @property
    def ogg(self) -> "Ogg":
        return self._to_audio(Ogg)

    @property
    def oga(self) -> "Oga":
        return self._to_audio(Oga)

    @property
    def opus(self) -> "Opus":
        return self._to_audio(Opus)


class Flac(Audio):
    __extension__ = Extension.FLAC


class Wav(Audio):
    __extension__ = Extension.WAV


class Mp3(Audio):
    __extension__ = Extension.MP3


class Ogg(Audio):
    __extension__ = Extension.OGG


class Oga(Ogg):
    __extension__ = Extension.OGA


class Opus(Ogg):
    __extension__ = Extension.OPUS
