from .codec import AudioCodec

from iokit.scheme.waveform import Waveform
from io import BytesIO
import soundfile


class SoundfileAudioCodec(AudioCodec):
    def encode(self, waveform: Waveform, extension: str) -> bytes:
        target = BytesIO()
        soundfile.write(
            file=target,
            data=waveform.wave,
            samplerate=waveform.freq,
            format=extension,
        )
        return target.getvalue()

    def decode(self, data: BytesIO) -> Waveform:
        wave, freq = soundfile.read(data, always_2d=True)
        return Waveform(wave=wave, freq=freq)
