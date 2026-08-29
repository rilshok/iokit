"""Audio waveforms with sample rate metadata."""

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
    """Audio waveform with shape (frames, channels) at a sample rate."""

    wave: NDArray[float32]
    freq: int

    def __post_init__(self) -> None:
        """Validate and normalize wave array to 2D with float32 dtype."""
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
        """Number of audio frames (samples per channel)."""
        return self.wave.shape[0]

    @property
    def channels(self) -> int:
        """Number of audio channels."""
        return self.wave.shape[1]

    def channel(self, index: int) -> "Waveform":
        """Extract a single channel as a new waveform."""
        return Waveform(self.wave[:, index], self.freq)

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.frames / self.freq

    def copy(self) -> "Waveform":
        """Create a deep copy of the waveform."""
        return Waveform(self.wave.copy(), self.freq)

    def _position(self, time: float) -> int:
        """Convert time in seconds to sample position."""
        return int(time * self.freq)

    def cut(self, begin: float | None = None, end: float | None = None) -> "Waveform":
        """Extract a time slice from the waveform.

        Args:
            begin: Start time in seconds (default: beginning).
            end: End time in seconds (default: end).

        Returns:
            A new waveform containing the slice.

        """
        if begin is None and end is None:
            return self.copy()
        begin, end = begin or 0.0, end or self.duration
        start, stop = self._position(begin), self._position(end)
        stop = min(stop, self.wave.shape[0])
        return Waveform(self.wave[start:stop], self.freq)

    def _repr_html_(self) -> str:
        """Return HTML audio player for notebook display."""
        source = self.to_ogg().data.base64
        return f'<audio controls src="data:audio/ogg;base64,{source}"></audio>'

    def to_mono(self) -> "Waveform":
        """Convert to single-channel waveform by averaging channels."""
        if self.channels == 1:
            return self.copy()
        return Waveform(self.wave.mean(axis=1), self.freq)

    def _to_audio(
        self,
        kls: type[A],
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> A:
        """Create an audio state of the specified type."""
        return kls(data=self, stem=stem, path=path, timestamp=timestamp)

    def to_wav(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Wav:
        """Create a WAV audio state from this waveform."""
        return self._to_audio(Wav, stem=stem, path=path, timestamp=timestamp)

    def to_flac(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Flac:
        """Create a FLAC audio state from this waveform."""
        return self._to_audio(Flac, stem=stem, path=path, timestamp=timestamp)

    def to_mp3(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Mp3:
        """Create an MP3 audio state from this waveform."""
        return self._to_audio(Mp3, stem=stem, path=path, timestamp=timestamp)

    def to_ogg(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Ogg:
        """Create an OGG audio state from this waveform."""
        return self._to_audio(Ogg, stem=stem, path=path, timestamp=timestamp)

    def to_oga(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Oga:
        """Create an OGA audio state from this waveform."""
        return self._to_audio(Oga, stem=stem, path=path, timestamp=timestamp)

    def to_opus(
        self,
        stem: str | None = None,
        path: str | None = None,
        timestamp: float | None = None,
    ) -> Opus:
        """Create an Opus audio state from this waveform."""
        return self._to_audio(Opus, stem=stem, path=path, timestamp=timestamp)
