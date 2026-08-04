from collections.abc import Generator, Iterable
from importlib import import_module
from typing import TYPE_CHECKING, Any, Self, TypeVar

from iokit.codec.base import best_codec

from .state import Data, LoadedState, State

if TYPE_CHECKING:
    from iokit.utils.waveform import Waveform

T = TypeVar("T", bound=object)


class FormatState(LoadedState[T]):
    __extension__: str
    __expected__: type[T] | None = None

    def __init__(self, data: T | Data, key: str, timestamp: float | None = None) -> None:
        self._assert_key(key)
        if isinstance(data, Data):
            super().__init__(data=data, key=key, timestamp=timestamp)
        else:
            with best_codec(key).encode(data) as content:
                super().__init__(data=content.read(), key=key, timestamp=timestamp)

    @classmethod
    def _assert_key(cls, key: str) -> None:
        if key.endswith(cls.__extension__):
            return
        msg = ""
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
    __extension__ = ".dat"
    __expected__ = bytes


class Bin(Dat):
    __extension__ = ".bin"


class Json(FormatState[dict[str, Any] | list[Any] | str]):
    __extension__ = ".json"
    __expected__ = dict | list | str


class Jsonl(Json):
    __extension__ = ".jsonl"


class Zip(Iterable[State[Any]]):
    __extension__ = ".zip"
    __expected__ = Generator


A = TypeVar("A", bound="Audio")


class Audio(FormatState["Waveform"]):
    def load(self, **config: object) -> "Waveform":
        return self._load(
            expected_type=import_module("iokit.utils.waveform").Waveform,
            codec=None,
            **config,
        )

    def _to_audio(self, kls: type[A]) -> A:
        self._assert_key(self.key)
        new_key = self.key.removesuffix(self.__extension__) + kls.__extension__
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
    __extension__ = ".flac"


class Wav(Audio):
    __extension__ = ".wav"


class Mp3(Audio):
    __extension__ = ".mp3"


class Ogg(Audio):
    __extension__ = ".ogg"


class Oga(Ogg):
    __extension__ = ".oga"


class Opus(Ogg):
    __extension__ = ".opus"
