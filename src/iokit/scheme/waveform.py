from dataclasses import dataclass
from numpy.typing import NDArray
from numpy import float32


@dataclass
class Waveform:
    wave: NDArray[float32]
    freq: int

    @property
    def duration(self) -> float:
        return self.wave.shape[0] / self.freq

    def copy(self) -> "Waveform":
        return Waveform(self.wave.copy(), self.freq)

    def cut(self, *, begin: float | None = None, end: float | None = None) -> "Waveform":
        if begin is None and end is None:
            return self.copy()
        raise NotImplementedError()

    def display(self):
        from IPython.display import Audio, display

        return display(Audio(self.wave, rate=self.freq))
