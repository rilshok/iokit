__all__ = ["auto_state"]

from datetime import datetime
from typing import Any, Literal

from numpy import ndarray
from pandas import DataFrame

from iokit.state import State, StateName

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
    name: str | StateName = "",
    *,
    compression: int | bool | None = None,
    password: str | None = None,
    waveform_to: Literal["wav", "flac", "mp3", "ogg"] = "wav",
    dataframe_to: Literal["csv", "tsv"] = "csv",
    builtin_to: Literal["json", "yaml"] = "json",
    time: datetime | None = None,
) -> State:
    if password is not None:
        state = auto_state(
            content,
            name=name,
            time=time,
            compression=compression,
            waveform_to=waveform_to,
            dataframe_to=dataframe_to,
            builtin_to=builtin_to,
        )
        return Enc(state, password=password, name=name, time=time)
    if compression is not None:
        state = auto_state(
            content,
            name=name,
            time=time,
            waveform_to=waveform_to,
            dataframe_to=dataframe_to,
            builtin_to=builtin_to,
        )
        return Gzip(state, name=name, time=time, compression=int(compression))
    match content:
        case ndarray():
            return Npy(content, name=name, time=time)
        case DataFrame():
            match dataframe_to:
                case "csv":
                    return Csv(content, name=name, time=time)
                case "tsv":
                    return Tsv(content, name=name, time=time)
        case Waveform():
            match waveform_to:
                case "wav":
                    return content.to_wav(name=name, time=time)
                case "flac":
                    return content.to_flac(name=name, time=time)
                case "mp3":
                    return content.to_mp3(name=name, time=time)
                case "ogg":
                    return content.to_ogg(name=name, time=time)
        case SecretState():
            return Enc(content, name=name, time=time)
        case bytes():
            return Dat(content, name=name, time=time)
        case str():
            return Txt(content, name=name, time=time)
        case dict() | int() | float() | bool():
            match builtin_to:
                case "json":
                    return Json(content, name=name, time=time)
                case "yaml":
                    return Yaml(content, name=name, time=time)
        case other:
            msg = f"Unsupported record: {other}"
            raise ValueError(msg)
