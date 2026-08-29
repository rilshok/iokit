"""Typed I/O with automatic codec selection from file extensions."""

__all__ = [
    "Archive",
    "Audio",
    "Bin",
    "BinaryStorage",
    "BufferedState",
    "CachedStorage",
    "CountingStorage",
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
    "LocalStorage",
    "MemoryStorage",
    "Mp3",
    "Npy",
    "Oga",
    "Ogg",
    "Ogx",
    "Opus",
    "Pandas",
    "Png",
    "State",
    "StateStorage",
    "Storage",
    "StreamLocalStorage",
    "StreamMemoryStorage",
    "Tar",
    "Tsv",
    "Txt",
    "Wav",
    "Waveform",
    "Yaml",
    "Yml",
    "Zip",
    "file",
    "filtrate",
    "first",
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
    Ogx,
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
    filtrate,
    first,
)
from .storage import (
    BinaryStorage,
    CachedStorage,
    CountingStorage,
    LocalStorage,
    MemoryStorage,
    StateStorage,
    Storage,
    StreamLocalStorage,
    StreamMemoryStorage,
)
from .utils.file import file

if TYPE_CHECKING:
    from .dtype.waveform import Waveform
    from .utils.web import web

_LAZY = {
    # each rests on a dependency of the `ultra` extra, unasked for at import time
    "Waveform": "iokit.dtype.waveform",
    "web": "iokit.utils.web",
    "S3Storage": "iokit.storage.s3",
    "StreamS3Storage": "iokit.storage.s3",
}


def __getattr__(name: str) -> Any:  # noqa: ANN401
    """Serve what rests on optional dependencies, without asking for them at import time."""
    if module := _LAZY.get(name):
        return getattr(import_module(module), name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
