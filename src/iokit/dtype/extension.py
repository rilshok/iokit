from enum import Enum

from iokit.utils.pattern import Pattern


class Extension(Enum):
    DAT = ".dat"
    BIN = ".bin"
    JSON = ".json"
    JSONL = ".jsonl"
    ZIP = ".zip"
    FLAC = ".flac"
    WAV = ".wav"
    MP3 = ".mp3"
    OGG = ".ogg"
    OGA = ".oga"
    OPUS = ".opus"

    def pattern(self) -> Pattern:
        return Pattern(f"*{self.value}")
