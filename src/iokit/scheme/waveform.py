from dataclasses import dataclass
from numpy.typing import NDArray
from numpy import float32


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
    def duration(self) -> float:
        return self.wave.shape[0] / self.freq

    def copy(self) -> "Waveform":
        return Waveform(self.wave.copy(), self.freq)

    def cut(self, *, begin: float | None = None, end: float | None = None) -> "Waveform":
        if begin is None and end is None:
            return self.copy()
        begin = begin or 0.0
        end = end or self.duration
        raise NotImplementedError()

    def display(self):
        from IPython.display import Audio, display

        return display(Audio(self.wave.T, rate=self.freq))
