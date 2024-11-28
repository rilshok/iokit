from iokit.state import State
from iokit.scheme.waveform import Waveform
from typing import Any
from .backend.audio.adapter import AdapterAudioCodec, AudioBackend
from .backend.audio.codec import AudioCodec


def _default_audiocodec() -> AudioCodec:
    return AdapterAudioCodec(backend="soundfile")


class AudioState(State, suffix=""):
    def __init__(self, waveform: Waveform, *, backend: AudioBackend = "soundfile", **kwargs: Any):
        super().__init__(
            data=AdapterAudioCodec(backend=backend).encode(
                waveform=waveform,
                extension=self._suffix,
            ),
            **kwargs,
        )

    def load(self) -> Waveform:
        return _default_audiocodec().decode(data=self.data)


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
