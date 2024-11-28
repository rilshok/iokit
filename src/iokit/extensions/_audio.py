from iokit.state import State
from typing import Any
from dataclasses import dataclass
from numpy.typing import NDArray
from numpy import float32
from io import BytesIO
import soundfile


class AudioState(State, suffix=""):
    def __init__(self, waveform: "Waveform", **kwargs: Any):
        soundfile.write(
            file=(target := BytesIO()),
            data=waveform.wave,
            samplerate=waveform.freq,
            format=self._suffix,
        )
        super().__init__(data=target.getvalue(), **kwargs)

    def load(self) -> "Waveform":
        wave, freq = soundfile.read(self.data, always_2d=True)
        return Waveform(wave=wave, freq=freq)


class Flac(AudioState, suffix="flac"):
    pass


class Wav(AudioState, suffix="wav"):
    pass


class Mp3(AudioState, suffix="mp3"):
    pass


class Ogg(AudioState, suffix="ogg"):
    pass


class Oga(AudioState, suffix="oga"):
    pass


@dataclass
class Waveform:
    wave: NDArray[float32]
    freq: int

    def __post_init__(self) -> None:
        if self.wave.ndim == 1:
            self.wave = self.wave[:, None]
        if self.wave.ndim != 2:
            msg = f"Waveform must be 1D or 2D array, but got {self.wave.ndim}D"
            raise ValueError(msg)
        if self.wave.shape[1] >= self.wave.shape[0]:
            msg = (
                "Waveform must have more frames than channels,"
                f" but got {self.wave.shape[0]} frames and {self.wave.shape[1]} channels."
            )
            raise ValueError(msg)
        if self.wave.dtype is not float32:
            self.wave = self.wave.astype(float32)

    @property
    def channels(self) -> int:
        return self.wave.shape[1]

    @property
    def duration(self) -> float:
        return self.wave.shape[0] / self.freq

    def copy(self) -> "Waveform":
        return Waveform(self.wave.copy(), self.freq)

    def _position(self, time: float) -> int:
        return int(time * self.freq)

    def cut(self, begin: float | None = None, end: float | None = None) -> "Waveform":
        if begin is None and end is None:
            return self.copy()
        begin, end = begin or 0.0, end or self.duration
        start, stop = self._position(begin), self._position(end)
        if stop > self.wave.shape[0]:
            stop = self.wave.shape[0]
        return Waveform(self.wave[start:stop], self.freq)

    def display(self):
        from IPython.display import Audio, display

        return display(Audio(self.wave.T, rate=self.freq))

    def to_mono(self) -> "Waveform":
        if self.channels == 1:
            return self.copy()
        return Waveform(self.wave.mean(axis=1), self.freq)

    def to_flac(self, name: str, **kwargs: Any) -> Flac:
        return Flac(waveform=self, name=name, **kwargs)

    def to_wav(self, name: str, **kwargs: Any) -> Wav:
        return Wav(waveform=self, name=name, **kwargs)

    def to_mp3(self, name: str, **kwargs: Any) -> Mp3:
        return Mp3(waveform=self, name=name, **kwargs)

    def to_ogg(self, name: str, **kwargs: Any) -> Ogg:
        return Ogg(waveform=self, name=name, **kwargs)
