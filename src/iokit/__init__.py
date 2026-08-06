__all__ = [
    "Archive",
    "Audio",
    "Bin",
    "BufferedState",
    "Csv",
    "Dat",
    "Data",
    "Document",
    "Enc",
    "Env",
    "FileState",
    "Flac",
    "FormatState",
    "Gzip",
    "Image",
    "Jpeg",
    "Jpg",
    "Json",
    "Jsonl",
    "LayerState",
    "LoadedState",
    "Mp3",
    "Npy",
    "Oga",
    "Ogg",
    "Opus",
    "Pandas",
    "Png",
    "State",
    "Tar",
    "Tsv",
    "Txt",
    "Wav",
    "Waveform",
    "Yaml",
    "Yml",
    "Zip",
    "file",
    "filter_states",
    "find_state",
    "web",
]

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .dtype.data import Data
from .state import (
    Archive,
    Audio,
    Bin,
    BufferedState,
    Csv,
    Dat,
    Document,
    Enc,
    Env,
    FileState,
    Flac,
    FormatState,
    Gzip,
    Image,
    Jpeg,
    Jpg,
    Json,
    Jsonl,
    LayerState,
    LoadedState,
    Mp3,
    Npy,
    Oga,
    Ogg,
    Opus,
    Pandas,
    Png,
    State,
    Tar,
    Tsv,
    Txt,
    Wav,
    Yaml,
    Yml,
    Zip,
    filter_states,
    find_state,
)
from .utils.file import file
from .utils.web import web

if TYPE_CHECKING:
    from .dtype.waveform import Waveform


def __getattr__(name: str) -> Any:  # noqa: ANN401
    """Serve `Waveform`, which rests on numpy, without asking for it at import time."""
    if name == "Waveform":
        return import_module("iokit.dtype.waveform").Waveform
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
