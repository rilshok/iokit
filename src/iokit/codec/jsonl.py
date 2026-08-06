__all__ = ["JsonlCodec"]

import json
from io import BytesIO
from typing import Any, BinaryIO

from jsonlines import Reader, Writer

from iokit.codec.base import Codec

D = list[Any]


class JsonlCodec(Codec[D]):
    def __init__(
        self,
        *,
        compact: bool = True,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
    ) -> None:
        self._compact = compact
        self._ensure_ascii = ensure_ascii
        self._allow_nan = allow_nan
        item_sep = "," if compact else ", "
        key_sep = ":" if compact else ": "
        self._dumps = json.JSONEncoder(
            ensure_ascii=ensure_ascii,
            allow_nan=allow_nan,
            sort_keys=False,
            separators=(item_sep, key_sep),
        ).encode

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"compact={self._compact}, "
            f"ensure_ascii={self._ensure_ascii}, "
            f"allow_nan={self._allow_nan}"
            ")"
        )

    def encode(self, data: D) -> BytesIO:
        buffer = BytesIO()
        with Writer(buffer, compact=self._compact, sort_keys=False, dumps=self._dumps) as writer:
            for item in data:
                writer.write(item)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> D:
        with buffer, Reader(buffer) as reader:
            return list(reader)
