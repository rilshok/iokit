__all__ = [
    "FlacSoundfileCodec",
    "Mp3SoundfileCodec",
    "OggSoundfileCodec",
    "OpusSoundfileCodec",
    "WavSoundfileCodec",
]

from io import BytesIO
from typing import BinaryIO

import soundfile

from iokit.codec.base import Codec
from iokit.dtype.waveform import Waveform

#: Frames written at a time. Handed a whole wave at once, libsndfile lays out four bytes of
#: stack for every frame of it, so a long enough one overruns the stack of the process.
BLOCK_FRAMES = 1 << 16


class _SoundfileCodec(Codec[Waveform]):
    """Reads and writes a waveform with libsndfile, which works on the buffer directly."""

    # The libsndfile container, and the encoding within it. A subtype of `None` leaves the
    # choice to libsndfile, which picks the default one of the container.
    __format_name__: str
    __subtype__: str | None = None

    def __init__(self, subtype: str | None = None) -> None:
        self._subtype = subtype or self.__subtype__

    def __repr__(self) -> str:
        return f"{type(self).__name__}(subtype={self._subtype})"

    def encode(self, data: Waveform) -> BytesIO:
        buffer = BytesIO()
        with soundfile.SoundFile(
            file=buffer,
            mode="w",
            samplerate=data.freq,
            channels=data.channels,
            format=self.__format_name__,
            subtype=self._subtype,
        ) as file:
            for start in range(0, data.frames, BLOCK_FRAMES):
                file.write(data.wave[start : start + BLOCK_FRAMES])
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Waveform:
        with buffer:
            wave, freq = soundfile.read(buffer, always_2d=True, dtype="float32")
        return Waveform(wave=wave, freq=freq)


class WavSoundfileCodec(_SoundfileCodec):
    __format_name__ = "WAV"


class FlacSoundfileCodec(_SoundfileCodec):
    __format_name__ = "FLAC"


class Mp3SoundfileCodec(_SoundfileCodec):
    __format_name__ = "MP3"


class OggSoundfileCodec(_SoundfileCodec):
    __format_name__ = "OGG"
    __subtype__ = "VORBIS"


class OpusSoundfileCodec(_SoundfileCodec):
    # Opus lives in an ogg container, and accepts only a handful of sample rates.
    __format_name__ = "OGG"
    __subtype__ = "OPUS"
