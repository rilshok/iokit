__all__ = ["Flac", "Mp3", "Ogg", "Wav", "Waveform"]

from contextlib import suppress
from datetime import datetime
from io import BytesIO

import soundfile

from iokit.utils.state import State, StateName
from iokit.utils.waveform import Waveform


class AudioState(State, suffix=""):
    def __init__(
        self,
        data: "Waveform",
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            soundfile.write(
                file=buffer,
                data=data.wave,
                samplerate=data.freq,
                format=self._suffix,
            )
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> "Waveform":
        fallbacks = (
            self._load_by_soundfile,
            self._load_by_torchaudio,
        )
        skip_exceptions = (soundfile.LibsndfileError,)
        suggestions: list[str] = []
        for fallback in fallbacks:
            with suppress(skip_exceptions):
                try:
                    return fallback()
                except ModuleNotFoundError as exc:
                    msg = f"{exc}. You may install this package and try again."
                    suggestions.append(msg)

        msg = "Failed to load audio data."
        if suggestions:
            additional = " ".join(suggestions)
            msg += f" Suggestions: {additional}"
        raise RuntimeError(msg)

    def _load_by_soundfile(self) -> "Waveform":
        wave, freq = soundfile.read(self.buffer, always_2d=True)
        return Waveform(wave=wave, freq=freq)

    def _load_by_torchaudio(self) -> "Waveform":
        from torchaudio import load

        from iokit.storage.local import save_temp

        with save_temp(self.buffer) as temp:
            path = temp.rename(temp.with_suffix(f".{self._suffix}"))
            wave_t, freq = load(path.as_posix())
        if wave_t.ndim == 1:
            wave_t = wave_t[:, None]
        return Waveform(wave=wave_t.T.numpy(), freq=freq)


class Flac(AudioState, suffix="flac"):
    pass


class Wav(AudioState, suffix="wav"):
    pass


class Mp3(AudioState, suffix="mp3"):
    pass


class Ogg(AudioState, suffix="ogg", suffixes=("ogg", "oga", "opus")):
    pass
