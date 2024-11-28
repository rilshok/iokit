from abc import ABC, abstractmethod

from iokit.scheme.waveform import Waveform
from io import BytesIO


class AudioCodec(ABC):
    @abstractmethod
    def encode(self, waveform: Waveform, extension: str) -> bytes:
        raise NotImplementedError()

    @abstractmethod
    def decode(self, data: BytesIO) -> Waveform:
        raise NotImplementedError()
