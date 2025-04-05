__all__ = ["auto_state"]

from datetime import datetime
from typing import Literal

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


def auto_state(  # noqa: C901, PLR0911, PLR0913, PLR0912
    data: object,
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
            data,
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
            data,
            name=name,
            time=time,
            waveform_to=waveform_to,
            dataframe_to=dataframe_to,
            builtin_to=builtin_to,
        )
        return Gzip(state, time=time, compression=int(compression))
    match data:
        case ndarray():
            return Npy(data, name=name, time=time)
        case DataFrame():
            match dataframe_to:
                case "csv":
                    return Csv(data, name=name, time=time)
                case "tsv":
                    return Tsv(data, name=name, time=time)
        case Waveform():
            match waveform_to:
                case "wav":
                    return data.to_wav(name=name, time=time)
                case "flac":
                    return data.to_flac(name=name, time=time)
                case "mp3":
                    return data.to_mp3(name=name, time=time)
                case "ogg":
                    return data.to_ogg(name=name, time=time)
        case SecretState():
            return Enc(data, name=name, time=time)
        case bytes():
            return Dat(data, name=name, time=time)
        case str():
            return Txt(data, name=name, time=time)
        case dict() | int() | float() | bool():
            match builtin_to:
                case "json":
                    return Json(data, name=name, time=time)
                case "yaml":
                    return Yaml(data, name=name, time=time)
        case other:
            msg = f"Unsupported record: {other}"
            raise ValueError(msg)
