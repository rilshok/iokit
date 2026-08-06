__all__ = ["CompressedNumpyCodec", "NumpyCodec"]

from io import BytesIO
from typing import Any, BinaryIO, TypeVar, cast

import numpy as np
from numpy.typing import NDArray

from iokit.codec.base import Codec

D = NDArray[Any]
M = dict[str, D]

T = TypeVar("T", bound=object)

# numpy's own name for an unnamed array; an archive holding it alone decodes back to a lone
# array instead of a mapping.
_LONE_NAME = "arr_0"

# Members are written as keyword arguments, so these names are not available to a mapping.
_RESERVED_NAMES = frozenset({"file", "allow_pickle", _LONE_NAME})


def _members(data: D | M) -> M:
    """The archive members of a lone array or of an already named mapping."""
    if isinstance(data, np.ndarray):
        return {_LONE_NAME: data}
    reserved = sorted(_RESERVED_NAMES.intersection(data))
    if reserved:
        names = ", ".join(repr(name) for name in reserved)
        msg = f"Array names reserved by the npz writer cannot be used: {names}"
        raise ValueError(msg)
    return data


def _reject_objects(members: M) -> None:
    """`np.savez_compressed` has no `allow_pickle` switch, so object arrays are refused here."""
    objects = sorted(name for name, array in members.items() if array.dtype == object)
    if objects:
        names = ", ".join(repr(name) for name in objects)
        msg = f"Object arrays require pickling, which is disabled: {names}"
        raise ValueError(msg)


class _NumpyCodec(Codec[T]):
    def __init__(self, *, allow_pickle: bool = False) -> None:
        self._allow_pickle = allow_pickle

    def __repr__(self) -> str:
        return f"{type(self).__name__}(allow_pickle={self._allow_pickle})"


class NumpyCodec(_NumpyCodec[D]):
    def encode(self, data: D) -> BytesIO:
        buffer = BytesIO()
        np.save(buffer, data, allow_pickle=self._allow_pickle)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> D:
        with buffer:
            array: D = np.load(buffer, allow_pickle=self._allow_pickle)
            return array


class CompressedNumpyCodec(_NumpyCodec[D | M]):
    """Stores either a lone array or a mapping of named arrays, and gives back what it stored."""

    def encode(self, data: D | M) -> BytesIO:
        members = _members(data)
        if not self._allow_pickle:
            _reject_objects(members)
        buffer = BytesIO()
        np.savez_compressed(buffer, **cast("dict[str, Any]", members))
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> D | M:
        # Members are read lazily, so they are materialized before the archive closes.
        with buffer, np.load(buffer, allow_pickle=self._allow_pickle) as archive:
            if archive.files == [_LONE_NAME]:
                lone: D = archive[_LONE_NAME]
                return lone
            return {name: archive[name] for name in archive.files}
