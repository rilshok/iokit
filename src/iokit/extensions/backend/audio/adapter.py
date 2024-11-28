from .codec import AudioCodec
from typing import Literal
from iokit.scheme.waveform import Waveform
from io import BytesIO
from .soundfile import SoundfileAudioCodec

AudioBackend = Literal["soundfile", "ffmpeg"]


class AdapterAudioCodec(AudioCodec):
    def __init__(self, backend: AudioBackend):
        self._backend: AudioCodec
        match backend:
            case "soundfile":
                self._backend = SoundfileAudioCodec()
            case "ffmpeg":
                raise NotImplementedError()
            case other:
                msg = f"Unknown backend: {other}"
                raise ValueError(msg)

    def encode(self, waveform: Waveform, extension: str) -> bytes:
        return self._backend.encode(waveform=waveform, extension=extension)

    def decode(self, data: BytesIO) -> Waveform:
        return self._backend.decode(data)
