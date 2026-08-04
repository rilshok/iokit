from collections.abc import Iterable
from importlib import import_module
from typing import TYPE_CHECKING, Any, Self, TypeVar

from .codec.base import best_codec
from .dtype.extension import Extension
from .state import Data, LoadedState, State

if TYPE_CHECKING:
    from types import UnionType

    from numpy.typing import NDArray  # noqa: F401
    from pandas import DataFrame  # noqa: F401
    from PIL.Image import Image as PillowImage  # noqa: F401

    from iokit.dtype.waveform import Waveform  # noqa: F401

T = TypeVar("T", bound=object)


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
