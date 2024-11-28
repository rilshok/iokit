from .codec import AudioCodec
from typing import Literal
from iokit.scheme.waveform import Waveform
from io import BytesIO


AudioBackend = Literal["soundfile", "librosa", "torchaudio"]


class AdapterAudioCodec(AudioCodec):
    def __init__(self, backend: AudioBackend):
        self._backend: AudioCodec
        match backend:
            case "soundfile":
                from .soundfile import SoundfileAudioCodec

                self._backend = SoundfileAudioCodec()
            case "librosa":
                raise NotImplementedError()
                # from .librosa import LibrosaAudioCodec
                # self._backend = LibrosaAudioCodec()
            case "torchaudio":
                # from .torchaudio import TorchaudioAudioCodec
                # self._backend = TorchaudioAudioCodec()
                raise NotImplementedError()
            case other:
                msg = f"Unknown backend: {other}"
                raise ValueError(msg)

    def encode(self, waveform: Waveform, extension: str) -> bytes:
        return self._backend.encode(waveform=waveform, extension=extension)

    def decode(self, data: BytesIO) -> Waveform:
        return self._backend.decode(data)
