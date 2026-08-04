from collections.abc import Generator, Iterable
from importlib import import_module
from typing import TYPE_CHECKING, Any, Self, TypeVar

from .codec.base import best_codec
from .dtype.extension import Extension
from .state import Data, LoadedState, State

if TYPE_CHECKING:
    from iokit.dtype.waveform import Waveform

T = TypeVar("T", bound=object)


class FormatState(LoadedState[T]):
    __extension__: Extension
    __expected__: type[T] | None = None

    def __init__(self, data: T | Data, key: str, timestamp: float | None = None) -> None:
        self._assert_key(key)
        if isinstance(data, Data):
            super().__init__(data=data, key=key, timestamp=timestamp)
        else:
            with best_codec(key).encode(data) as content:
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
    def from_state(cls, state: State[Any]) -> Self:
        cls._assert_key(state.key)
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


class Dat(FormatState[bytes]):
    __extension__ = Extension.DAT
    __expected__ = bytes


class Bin(Dat):
    __extension__ = Extension.BIN


class Json(FormatState[dict[str, Any] | list[Any] | str]):
    __extension__ = Extension.JSON
    __expected__ = dict | list | str


class Jsonl(Json):
    __extension__ = Extension.JSONL


class Zip(Iterable[State[Any]]):
    __extension__ = Extension.ZIP
    __expected__ = Generator


A = TypeVar("A", bound="Audio")


class Audio(FormatState["Waveform"]):
    def load(self, **config: object) -> "Waveform":
        return self._load(
            expected_type=import_module("iokit.dtype.waveform").Waveform,
            codec=None,
            **config,
        )

    def _to_audio(self, kls: type[A]) -> A:
        self._assert_key(self.key)
        new_key = self.key.removesuffix(self.extension()) + kls.extension()
        return kls(data=self.load(), key=new_key, timestamp=self.timestamp)

    def to_flac(self) -> "Flac":
        return self._to_audio(Flac)

    def to_wav(self) -> "Wav":
        return self._to_audio(Wav)

    def to_mp3(self) -> "Mp3":
        return self._to_audio(Mp3)

    def to_ogg(self) -> "Ogg":
        return self._to_audio(Ogg)

    def to_oga(self) -> "Oga":
        return self._to_audio(Oga)

    def to_opus(self) -> "Opus":
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
