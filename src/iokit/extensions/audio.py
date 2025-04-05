__all__ = ["Flac", "Mp3", "Ogg", "Wav", "Waveform"]

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import soundfile
from numpy import float32
from numpy.typing import NDArray

from iokit.state import State, StateName


class AudioState(State, suffix=""):
    def __init__(
        self,
        data: "Waveform",
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            soundfile.write(
                file=buffer,
                data=data.wave,
                samplerate=data.freq,
                format=self._suffix,
            )
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> "Waveform":
        wave, freq = soundfile.read(self.buffer, always_2d=True)
        return Waveform(wave=wave, freq=freq)


class Flac(AudioState, suffix="flac"):
    pass


class Wav(AudioState, suffix="wav"):
    pass


class Mp3(AudioState, suffix="mp3"):
    pass


class Ogg(AudioState, suffix="ogg", suffixes=("ogg", "oga", "opus")):
    pass


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
        if self.channels >= self.frames:
            msg = (
                "Waveform must have more frames than channels,"
                f" but got {self.frames} frames and {self.channels} channels."
            )
            raise ValueError(msg)
        if self.wave.dtype is not float32:
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
        from IPython.display import Audio, display

        return display(Audio(self.wave.T, rate=self.freq))

    def to_mono(self) -> "Waveform":
        if self.channels == 1:
            return self.copy()
        return Waveform(self.wave.mean(axis=1), self.freq)

    def to_flac(self, name: str | StateName, *, time: datetime | None = None) -> Flac:
        return Flac(self, name=name, time=time)

    def to_wav(self, name: str | StateName, *, time: datetime | None = None) -> Wav:
        return Wav(self, name=name, time=time)

    def to_mp3(self, name: str | StateName, *, time: datetime | None = None) -> Mp3:
        return Mp3(self, name=name, time=time)

    def to_ogg(self, name: str | StateName, *, time: datetime | None = None) -> Ogg:
        return Ogg(self, name=name, time=time)
