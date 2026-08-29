"""Codecs for audio files using torchaudio backend."""

__all__ = [
    "FlacTorchaudioCodec",
    "Mp3TorchaudioCodec",
    "OggTorchaudioCodec",
    "OpusTorchaudioCodec",
    "WavTorchaudioCodec",
]

from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

import torchaudio
from numpy import ascontiguousarray
from torch import from_numpy

from iokit.codec.base import Codec
from iokit.dtype.waveform import Waveform


@contextmanager
def _temp_path(extension: str) -> Iterator[Path]:
    """Create a path in a private directory, named so that torchaudio infers the format from it.

    Args:
        extension: File extension to use for the temporary audio file.

    Yields:
        A path object pointing to a temporary file with the given extension.

    """
    with TemporaryDirectory() as directory:
        yield Path(directory) / f"audio.{extension}"


class _TorchaudioCodec(Codec[Waveform]):
    """Reads and writes a waveform with torchaudio, which needs a file to know the format."""

    __extension__: str

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def encode(self, data: Waveform) -> BytesIO:
        # torchaudio lays a waveform out as channels by frames, the transpose of a `Waveform`.
        wave = from_numpy(ascontiguousarray(data.wave.T))
        with _temp_path(self.__extension__) as path:
            torchaudio.save(str(path), wave, sample_rate=data.freq)
            return BytesIO(path.read_bytes())

    def decode(self, buffer: BinaryIO) -> Waveform:
        with buffer, _temp_path(self.__extension__) as path:
            path.write_bytes(buffer.read())
            wave, freq = torchaudio.load(str(path))
        return Waveform(wave=wave.numpy().T, freq=freq)


class WavTorchaudioCodec(_TorchaudioCodec):
    """Codec for WAV audio files using torchaudio."""

    __extension__ = "wav"


class FlacTorchaudioCodec(_TorchaudioCodec):
    """Codec for FLAC audio files using torchaudio."""

    __extension__ = "flac"


class Mp3TorchaudioCodec(_TorchaudioCodec):
    """Codec for MP3 audio files using torchaudio."""

    __extension__ = "mp3"


class OggTorchaudioCodec(_TorchaudioCodec):
    """Codec for OGG audio files using torchaudio."""

    __extension__ = "ogg"


class OpusTorchaudioCodec(_TorchaudioCodec):
    """Codec for Opus audio files using torchaudio."""

    __extension__ = "opus"
