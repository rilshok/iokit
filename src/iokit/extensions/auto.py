__all__ = ["auto_state"]

from typing import Any, Literal

from numpy import ndarray
from pandas import DataFrame

from iokit.state import State

from .audio import Waveform
from .dat import Dat
from .enc import Enc, SecretState
from .gz import Gzip
from .json import Json
from .npy import Npy
from .table import Csv, Tsv
from .txt import Txt
from .yaml import Yaml


def auto_state(
    content: Any,
    /,
    name: str,
    *,
    compression: int | bool | None = None,
    password: str | None = None,
    waveform_to: Literal["wav", "flac", "mp3", "ogg"] = "wav",
    dataframe_to: Literal["csv", "tsv"] = "csv",
    builtin_to: Literal["json", "yaml"] = "json",
) -> State:
    if password is not None:
        state = auto_state(content, name=name, compression=compression)
        return Enc(state, password=password, name=name)
    if compression is not None:
        state = auto_state(content, name=name)
        return Gzip(state, compression=int(compression))
    match content:
        case ndarray():
            return Npy(content, name=name)
        case DataFrame():
            match dataframe_to:
                case "csv":
                    return Csv(content, name=name)
                case "tsv":
                    return Tsv(content, name=name)
        case Waveform():
            match waveform_to:
                case "wav":
                    return content.to_wav(name=name)
                case "flac":
                    return content.to_flac(name=name)
                case "mp3":
                    return content.to_mp3(name=name)
                case "ogg":
                    return content.to_ogg(name=name)
        case SecretState():
            return Enc(content, name=name)
        case bytes():
            return Dat(content, name=name)
        case str():
            return Txt(content, name=name)
        case dict() | int() | float() | bool():
            match builtin_to:
                case "json":
                    return Json(content, name=name)
                case "yaml":
                    return Yaml(content, name=name)
        case other:
            msg = f"Unsupported record: {other}"
            raise ValueError(msg)
