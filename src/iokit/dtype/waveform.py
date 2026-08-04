__all__ = ["Waveform"]

from dataclasses import dataclass
from typing import TypeVar

from numpy import float32
from numpy.typing import NDArray

from iokit.state import Audio, Flac, Mp3, Oga, Ogg, Opus, Wav

_MAX_CHANNELS = 8  # Maximum number of channels for a waveform

A = TypeVar("A", bound=Audio)


@dataclass
class Waveform:
    wave: NDArray[float32]
    freq: int

    def __post_init__(self) -> None:
        if self.wave.ndim == 1:
            self.wave = self.wave[:, None]
        if self.wave.ndim != 2:  # noqa: PLR2004
            msg = f"Waveform must be 1D or 2D array, but got {self.wave.ndim}D"
            raise ValueError(msg)
        if self.channels >= _MAX_CHANNELS:
            msg = (
                f"Waveform must have less than {_MAX_CHANNELS} channels,"
                f" but got {self.channels} channels."
            )
            raise ValueError(msg)
        if self.wave.dtype != float32:
            self.wave = self.wave.astype(float32)

    @property
    def frames(self) -> int:
        return self.wave.shape[0]

    @property
    def channels(self) -> int:
        return self.wave.shape[1]

    def channel(self, index: int) -> "Waveform":
        return Waveform(self.wave[:, index], self.freq)

    @property
    def duration(self) -> float:
        return self.frames / self.freq

    def copy(self) -> "Waveform":
        return Waveform(self.wave.copy(), self.freq)

    def _position(self, time: float) -> int:
        return int(time * self.freq)

    def cut(self, begin: float | None = None, end: float | None = None) -> "Waveform":
        if begin is None and end is None:
            return self.copy()
        begin, end = begin or 0.0, end or self.duration
        start, stop = self._position(begin), self._position(end)
        stop = min(stop, self.wave.shape[0])
        return Waveform(self.wave[start:stop], self.freq)

    def display(self) -> None:
        # TODO(@rilshok): rebase to _repr_html_
        from IPython.display import Audio, display

        return display(Audio(self.wave.T, rate=self.freq))

    def to_mono(self) -> "Waveform":
        if self.channels == 1:
            return self.copy()
        return Waveform(self.wave.mean(axis=1), self.freq)

    def _to_audio(self, kls: type[A], name: str, timestamp: float | None = None) -> A:
        if not name.lower().endswith(ext := kls.extension()):
            name += ext
        return kls(data=self, key=name, timestamp=timestamp)

    def to_wav(self, name: str, timestamp: float | None = None) -> Wav:
        return self._to_audio(Wav, name=name, timestamp=timestamp)

    def to_flac(self, name: str, timestamp: float | None = None) -> Flac:
        return self._to_audio(Flac, name=name, timestamp=timestamp)

    def to_mp3(self, name: str, timestamp: float | None = None) -> Mp3:
        return self._to_audio(Mp3, name=name, timestamp=timestamp)

    def to_ogg(self, name: str, timestamp: float | None = None) -> Ogg:
        return self._to_audio(Ogg, name=name, timestamp=timestamp)

    def to_oga(self, name: str, timestamp: float | None = None) -> Oga:
        return self._to_audio(Oga, name=name, timestamp=timestamp)

    def to_opus(self, name: str, timestamp: float | None = None) -> Opus:
        return self._to_audio(Opus, name=name, timestamp=timestamp)
