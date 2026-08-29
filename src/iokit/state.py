"""State classes for managing payloads with paths and timestamps."""

from collections.abc import Generator, Iterable, Iterator
from contextlib import contextmanager
from importlib import import_module
from io import SEEK_END, SEEK_SET, BufferedReader, BytesIO, RawIOBase
from os import utime
from pathlib import Path, PurePath
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, BinaryIO, Generic, TypeVar

from humanize import naturalsize
from typing_extensions import Self

from iokit.codec.base import best_codec
from iokit.dtype.data import Data
from iokit.dtype.extension import Extension
from iokit.utils.checksum import Hash
from iokit.utils.pattern import Pattern
from iokit.utils.time import Timestamp

if TYPE_CHECKING:
    from types import UnionType

    from _typeshed import WriteableBuffer
    from numpy.typing import NDArray  # noqa: F401
    from pandas import DataFrame  # noqa: F401
    from PIL.Image import Image as PillowImage  # noqa: F401

    from iokit.dtype.waveform import Waveform  # noqa: F401


T = TypeVar("T", bound=object)

PathLike = str | Path


class State(Generic[T]):
    """A payload with a path and timestamp."""

    def __init__(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Initialize a state with optional path and timestamp.

        Args:
            stem: Filename without extension, defaults to empty.
            path: Full path with extension; can be derived from `stem`.
            timestamp: Seconds since epoch; uses current time if None.

        """
        # the field rather than the property, which a subclass may hold shut against renaming
        self._path = self._resolve_path(stem=stem, path=path)
        self._timestamp = Timestamp.now() if timestamp is None else Timestamp(timestamp)

    @classmethod
    def extension(cls) -> str:
        """Return the file extension for this state kind.

        Returns:
            File extension string; empty for plain states.

        """
        return ""

    @classmethod
    def _assert_path(cls, path: str) -> None:
        if path.lower().endswith(cls.extension()):
            return
        msg = f"Path must end with {cls.extension()!r} extension"
        raise ValueError(msg)

    @classmethod
    def _strip_extension(cls, path: str) -> str:
        """Take the extension of this kind off `path`, in whatever case it is written."""
        # a slice rather than `removesuffix`, which `.GZ` would slip past the way `_assert_path`
        # does not, and rather than a bare negative one, which an empty extension would empty
        return path[: len(path) - len(cls.extension())]

    @classmethod
    def _resolve_path(cls, stem: str | None, path: str | None) -> str:
        """Resolve state path from stem or path, or both.

        Args:
            stem: Filename without extension.
            path: Full path with extension.

        Returns:
            The resolved path.

        """
        stem = None if stem is None else str(stem)
        path = None if path is None else str(path)
        extension = cls.extension()
        if path is None:
            # no name at all, so a state of nothing but the bare extension
            stem = stem if stem is not None else ""
            if extension and stem.lower().endswith(extension):
                msg = (
                    f"Stem {stem!r} already carries the {extension!r} extension, "
                    f"so it is a path: pass it as one"
                )
                raise ValueError(msg)
            return stem + extension
        cls._assert_path(path)
        # the stem is the path without its extension, directories kept or dropped
        if stem is not None and stem not in (PurePath(path).stem, cls._strip_extension(path)):
            msg = (
                f"Stem {stem!r} does not match the path {path!r}, "
                f"whose stem is {PurePath(path).stem!r}"
            )
            raise ValueError(msg)
        return path

    def __repr__(self) -> str:
        """Return a string representation of the state."""
        size = naturalsize(self.size, gnu=True)
        return f"{self.path} ({size})"

    @property
    def timestamp(self) -> Timestamp:
        """Return the modification timestamp.

        Returns:
            The timestamp value.

        """
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: float | None) -> None:
        self._timestamp = Timestamp.now() if value is None else Timestamp(value)

    @property
    def path(self) -> str:
        """Return the state's path."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._path = str(value)

    @property
    def name(self) -> str:
        """Return the filename with extension."""
        return PurePath(self._path).name

    @name.setter
    def name(self, value: str) -> None:
        self.path = PurePath(self._path).with_name(str(value)).as_posix()

    @property
    def stem(self) -> str:
        """Return the filename without extension."""
        return PurePath(self._path).stem

    @stem.setter
    def stem(self, value: str) -> None:
        self.path = PurePath(self._path).with_stem(str(value)).as_posix()

    @property
    def suffix(self) -> str:
        """Return the file extension."""
        return PurePath(self._path).suffix

    @suffix.setter
    def suffix(self, value: str) -> None:
        self.path = PurePath(self._path).with_suffix(str(value)).as_posix()

    @property
    def size(self) -> int:
        """Return the data size in bytes.

        Returns:
            Size in bytes.

        """
        return len(self.data)

    @property
    def data(self) -> Data:
        """Return the state's data content.

        Returns:
            The data.

        """
        with self.buffer as buffer:
            return Data(buffer.read())

    def digest(self, algorithm: str | Hash) -> Data:
        """Compute a digest of the state's data.

        Args:
            algorithm: Hashing algorithm to use.

        Returns:
            The digest.

        """
        with self.buffer as buffer:
            return Data.digest_from_io(algorithm, buffer)

    @property
    def buffer(self) -> BinaryIO:
        """Return a binary buffer of the state's data.

        Returns:
            BytesIO buffer.

        """
        return BytesIO(self.data)

    def _load(self, expected: "type[T] | UnionType | None", **config: object) -> T:
        data: T = best_codec(self.name, **config).decode(self.buffer)
        if expected is None or isinstance(data, expected):
            return data
        expectation = getattr(expected, "__name__", str(expected))
        msg = f"Expected loaded data of type '{expectation}', got '{type(data).__name__}'"
        raise TypeError(msg)

    def load(self, **config: object) -> T:
        """Decode the state's data.

        Args:
            **config: Codec options.

        Returns:
            The decoded payload.

        """
        return self._load(None, **config)

    def save(
        self,
        root: PathLike = "",
        *,
        parents: bool = False,
        force: bool = False,
    ) -> "FileState[T]":
        """Write the state to a file.

        Args:
            root: Directory to resolve path against; current directory by default.
            parents: Create missing parent directories.
            force: Overwrite existing file.

        Returns:
            The saved file state.

        Raises:
            ValueError: If path resolves outside `root`.
            FileExistsError: If file exists and `force` is not set.

        """
        root = Path(root).resolve()
        relative = PurePath(self.path)
        path = (root / relative.relative_to(relative.anchor)).resolve()
        if not path.is_relative_to(root):
            msg = f"Path is outside of root: root='{root!s}', path='{self.path!s}'"
            raise ValueError(msg)
        if path.exists() and not force:
            msg = f"File already exists: path='{path!s}'"
            raise FileExistsError(msg)
        root.mkdir(parents=parents, exist_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.buffer as source, path.open("wb") as target:
            copyfileobj(source, target)
        utime(path, (self.timestamp, self.timestamp))
        return FileState(path)

    @contextmanager
    def save_temp(self, root: PathLike | None = None) -> Generator["FileState[T]", None, None]:
        """Write state to a temporary file, removed on context exit.

        Args:
            root: Directory for temporary file; system temp if `None`.

        Yields:
            The saved file state.

        """
        with TemporaryDirectory(dir=root) as temp:
            yield self.save(temp)

    def gzip(self, *, compression: int = 1) -> "Gzip":
        """Compress this state as it stands.

        Args:
            compression: The gzip level, from 0 for none to 9 for the smallest output.

        Returns:
            The compressed state, pathed after this one with `.gz` appended.

        """
        return Gzip(self, compression=compression)

    def encrypt(self, *, password: bytes | str, salt: bytes | str = "") -> "Enc":
        """Encrypt the payload of this state as it stands.

        Args:
            password: The secret guarding the payload, to be repeated on decrypting.
            salt: Extra input to the key derivation, to be repeated on decrypting.

        Returns:
            The encrypted state, pathed after this one with `.enc` appended.

        """
        return Enc(self, password=password, salt=salt)


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
    """A state backed by an in-memory buffer."""

    def __init__(
        self,
        buffer: BinaryIO,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Initialize a state from a binary buffer.

        Args:
            buffer: A readable, seekable binary I/O buffer.
            stem: The name without extension, completing the path when left out.
            path: The full path including extension, completed from stem when left out.
            timestamp: The modification time in seconds since epoch; current time if None.

        Raises:
            ValueError: If the buffer is not readable or seekable.

        """
        self._source = buffer
        super().__init__(stem=stem, path=path, timestamp=timestamp)
        if not buffer.readable():
            msg = "Buffer must be readable"
            raise ValueError(msg)
        if not buffer.seekable():
            msg = "Buffer must be seekable"
            raise ValueError(msg)

    def __del__(self) -> None:
        """Close the underlying source buffer."""
        self._source.close()

    @property
    def buffer(self) -> BufferedReader:
        """Get a buffered reader for this state's data.

        Returns:
            A buffered reader wrapping the source buffer.

        """
        return BufferedReader(_StreamView(self._source))

    @property
    def size(self) -> int:
        """Get the size of the buffer in bytes.

        Returns:
            The number of bytes in the buffer.

        """
        return self._source.seek(0, SEEK_END)


class FileState(State[T]):
    """A state standing for a file on disk, read from it as it is asked for.

    Its path leads back to that file, and is held shut: renaming a state renames no file.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize a state from a file on disk.

        Args:
            path: The path to an existing file.

        Raises:
            FileNotFoundError: If the path is not a regular file.

        """
        file = Path(path)
        if not file.is_file():
            msg = "Path is not a regular file"
            raise FileNotFoundError(msg)
        super().__init__(path=file.as_posix(), timestamp=file.stat().st_mtime)

    @property
    def path(self) -> str:
        """Where the file this state stands for is, and where it stays."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:  # noqa: ARG002
        msg = "Cannot rename a state standing for a file on disk"
        raise AttributeError(msg)

    @property
    def buffer(self) -> BufferedReader:
        """Get a buffered reader for the file.

        Returns:
            An open file in binary read mode.

        """
        return Path(self._path).open("rb")

    @property
    def size(self) -> int:
        """Get the size of the file in bytes.

        Returns:
            The file size in bytes.

        """
        return Path(self._path).stat().st_size


class LoadedState(State[T]):
    """A state backed by data loaded in memory."""

    def __init__(
        self,
        data: bytes,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Initialize a state from raw data bytes.

        Args:
            data: The raw data bytes.
            stem: The name without extension, completing the path when left out.
            path: The full path including extension, completed from stem when left out.
            timestamp: The modification time in seconds since epoch; current time if None.

        """
        super().__init__(stem=stem, path=path, timestamp=timestamp)
        self._data = data

    @property
    def data(self) -> Data:
        """Get the data content of this state.

        Returns:
            The data as a Data object.

        """
        return Data(self._data)


class FormatState(LoadedState[T]):
    """A state of a known format, filed under a path its extension closes.

    `Json(document, "greeting")` is the state `greeting.json`; a path may be given instead,
    or both when they agree, or neither for a state filed under the bare extension.
    """

    __extension__: Extension
    # An unparameterized class, or a union of them, checked against the loaded payload. A type
    # coming from an optional dependency is named as "module:attribute", imported only on load.
    __expected__: "type[Any] | UnionType | str | None" = None

    def __init__(
        self,
        data: T | Data,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
        **config: object,
    ) -> None:
        """Encode a payload as this format.

        Args:
            data: The payload to encode, or the `Data` of an encoded one, taken as it stands.
            stem: The name with the extension left off, completing `path` when left out.
            path: The whole path, extension included, completed from `stem` when left out.
            timestamp: The modification time, the current one by default.
            **config: Settings for the codec doing the encoding.

        Raises:
            ValueError: If `stem` and `path` disagree, if `path` lacks the extension of this
                format, or if `config` is given for data already encoded.

        """
        path = self._resolve_path(stem=stem, path=path)
        if isinstance(data, Data):
            if config:
                msg = "Cannot configure a codec for already encoded data"
                raise ValueError(msg)
            super().__init__(data=data, path=path, timestamp=timestamp)
        else:
            with best_codec(path, **config).encode(self._to_encode(data)) as content:
                super().__init__(data=content.read(), path=path, timestamp=timestamp)

    @classmethod
    def extension(cls) -> str:
        """Get the file extension for this format state.

        Returns:
            The extension value as a string.

        """
        return cls.__extension__.value

    @classmethod
    def _to_encode(cls, data: T) -> object:
        """Get the data for encoding by the codec.

        The codec receives the payload unless a subclass specifies otherwise.

        Args:
            data: The payload to encode.

        Returns:
            The data to pass to the codec.

        """
        return data

    @classmethod
    def _expected(cls) -> "type[Any] | UnionType | None":
        """Get the expected type for the loaded payload.

        Imports the type if it was given as a named reference.

        Returns:
            The expected type for validation, or None if not specified.

        """
        if isinstance(cls.__expected__, str):
            module, _, attribute = cls.__expected__.partition(":")
            expected: type[Any] = getattr(import_module(module), attribute)
            return expected
        return cls.__expected__

    @classmethod
    def from_state(cls, state: State[Any]) -> Self:
        """Create a format state from another state.

        Args:
            state: A state with the correct file extension.

        Returns:
            A format state with the data from the given state.

        """
        cls._assert_path(state.path)
        return cls(data=state.data, path=state.path, timestamp=state.timestamp)

    def load(self, **config: object) -> T:
        """Load and decode the format state's data.

        Args:
            **config: Codec configuration options.

        Returns:
            The decoded payload, validated against the expected type.

        """
        return self._load(self._expected(), **config)


def filtrate(states: Iterable[State[T]], pattern: str | Pattern) -> Iterator[State[T]]:
    """Filter states by path pattern.

    Args:
        states: An iterable of states to filter.
        pattern: A pattern to match against state paths.

    Yields:
        States whose paths match the pattern.

    """
    pattern = Pattern(pattern)
    for state in states:
        if pattern(state.path):
            yield state


def first(states: Iterable[State[T]], pattern: str | Pattern) -> State[T]:
    """Get the first state matching a pattern.

    Args:
        states: An iterable of states to search.
        pattern: A pattern to match against state paths.

    Returns:
        The first state whose path matches the pattern.

    Raises:
        FileNotFoundError: If no matching state is found.

    """
    for state in filtrate(states, pattern):
        return state
    msg = f"State not found: {pattern!r}"
    raise FileNotFoundError(msg)


class Dat(FormatState[bytes]):
    """A binary data file state."""

    __extension__ = Extension.DAT
    __expected__ = bytes


class Bin(Dat):
    """A binary file state."""

    __extension__ = Extension.BIN


class Txt(FormatState[str]):
    """A plain text file state."""

    __extension__ = Extension.TXT
    __expected__ = str


class Document(FormatState[dict[str, Any] | list[Any] | str]):
    """A structured document: a mapping, a sequence, or a bare scalar string."""

    __expected__ = dict | list | str


class Json(Document):
    """A JSON document state."""

    __extension__ = Extension.JSON


class Jsonl(FormatState[list[dict[str, Any]]]):
    """JSON Lines: one record per line, so the payload is always a list of records."""

    __extension__ = Extension.JSONL
    __expected__ = list


class Yaml(Document):
    """A YAML document state."""

    __extension__ = Extension.YAML


class Yml(Yaml):
    """A YML document state (YAML variant)."""

    __extension__ = Extension.YML


class Env(FormatState[dict[str, str | None]]):
    """A dotenv file; a variable declared without a value loads as `None`."""

    __extension__ = Extension.ENV
    __expected__ = dict


class Npy(FormatState["NDArray[Any]"]):
    """A NumPy array state."""

    __extension__ = Extension.NPY
    __expected__ = "numpy:ndarray"


class Pandas(FormatState["DataFrame"]):
    """A dataframe stored as delimited text."""

    __expected__ = "pandas:DataFrame"


class Csv(Pandas):
    """A CSV file state."""

    __extension__ = Extension.CSV


class Tsv(Pandas):
    """A TSV (tab-separated values) file state."""

    __extension__ = Extension.TSV


class Image(FormatState["PillowImage"]):
    """A raster image, decoded by Pillow."""

    __expected__ = "PIL.Image:Image"


class Jpeg(Image):
    """A JPEG image state."""

    __extension__ = Extension.JPEG


class Jpg(Jpeg):
    """A JPG image state (JPEG variant)."""

    __extension__ = Extension.JPG


class Png(Image):
    """A PNG image state."""

    __extension__ = Extension.PNG


class Archive(FormatState[Iterable[State[Any]]]):
    """A container of whole states: loading one yields its members, lazily."""

    __expected__ = Iterable


class Zip(Archive):
    """A ZIP archive state."""

    __extension__ = Extension.ZIP


class Tar(Archive):
    """A TAR archive state."""

    __extension__ = Extension.TAR


class LayerState(FormatState[State[Any]]):
    """A state laid over another one: its payload goes through a layer, its path gains a suffix.

    `data.json` compressed is `data.json.gz`, and loading that gives `data.json` back. Only
    the payload travels through the layer, so a codec of plain bytes is all it takes.
    """

    def __init__(
        self,
        data: State[Any] | Data,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
        **config: object,
    ) -> None:
        """Initialize a layer state by wrapping another state.

        Args:
            data: A state to wrap or data to encode.
            stem: The name without extension, completing the path when left out.
            path: The full path including extension, completed from stem when left out.
            timestamp: The modification time, inherited from the wrapped state if left out.
            **config: Codec configuration options.

        """
        if isinstance(data, State):
            if stem is None and path is None:
                path = data.path + self.extension()
            if timestamp is None:
                timestamp = data.timestamp
        super().__init__(data, stem=stem, path=path, timestamp=timestamp, **config)

    @classmethod
    def _to_encode(cls, data: State[Any]) -> object:
        return data.data

    def load(self, **config: object) -> State[Any]:
        """Take the layer off, recovering the state it was laid over.

        Args:
            **config: Settings for the codec taking the layer off.

        Returns:
            The state under the layer, pathed the way this one is less the suffix.

        Raises:
            TypeError: If the codec of the layer gives back anything but bytes.

        """
        payload = best_codec(self.name, **config).decode(self.buffer)
        if not isinstance(payload, bytes):
            msg = f"Expected a layer of bytes, got '{type(payload).__name__}'"
            raise TypeError(msg)
        return LoadedState(
            payload,
            path=self._strip_extension(self.path),
            timestamp=self.timestamp,
        )


class Gzip(LayerState):
    """A compressed state: `data.json` becomes `data.json.gz`, an ordinary gzip file."""

    __extension__ = Extension.GZ


class Enc(LayerState):
    """An encrypted state: `data.json` becomes `data.json.enc`.

    The `password` and `salt` are given when encrypting, and again when loading:
    `state.encrypt(password="...").load(password="...")`.
    """

    __extension__ = Extension.ENC


A = TypeVar("A", bound="Audio")


class Audio(FormatState["Waveform"]):
    """A waveform audio file state."""

    __expected__ = "iokit.dtype.waveform:Waveform"

    def _to_audio(self, kls: type[A]) -> A:
        self._assert_path(self.path)
        path = self._strip_extension(self.path) + kls.extension()
        return kls(data=self.load(), path=path, timestamp=self.timestamp)

    @property
    def flac(self) -> "Flac":
        """Convert this audio to FLAC format.

        Returns:
            This audio as a FLAC state.

        """
        return self._to_audio(Flac)

    @property
    def wav(self) -> "Wav":
        """Convert this audio to WAV format.

        Returns:
            This audio as a WAV state.

        """
        return self._to_audio(Wav)

    @property
    def mp3(self) -> "Mp3":
        """Convert this audio to MP3 format.

        Returns:
            This audio as an MP3 state.

        """
        return self._to_audio(Mp3)

    @property
    def ogg(self) -> "Ogg":
        """Convert this audio to OGG format.

        Returns:
            This audio as an OGG state.

        """
        return self._to_audio(Ogg)

    @property
    def oga(self) -> "Oga":
        """Convert this audio to OGA format.

        Returns:
            This audio as an OGA state.

        """
        return self._to_audio(Oga)

    @property
    def opus(self) -> "Opus":
        """Convert this audio to Opus format.

        Returns:
            This audio as an Opus state.

        """
        return self._to_audio(Opus)


class Flac(Audio):
    """A FLAC audio file state."""

    __extension__ = Extension.FLAC


class Wav(Audio):
    """A WAV audio file state."""

    __extension__ = Extension.WAV


class Mp3(Audio):
    """An MP3 audio file state."""

    __extension__ = Extension.MP3


class Ogg(Audio):
    """An OGG audio file state."""

    __extension__ = Extension.OGG


class Oga(Ogg):
    """An OGA audio file state."""

    __extension__ = Extension.OGA


class Ogx(Ogg):
    """An OGX audio file state."""

    __extension__ = Extension.OGX


class Opus(Ogg):
    """An Opus audio file state."""

    __extension__ = Extension.OPUS
