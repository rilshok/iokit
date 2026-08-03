import json
from io import BytesIO
from typing import Any, BinaryIO

from iokit.utils.state_new import Codec

D = dict[str, Any] | list[Any] | str


class JsonCodec(Codec[D]):
    def __init__(
        self,
        *,
        compact: bool = False,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
    ) -> None:
        item_sep = "," if compact else ", "
        key_sep = ":" if compact else ": "
        self._dumps = json.JSONEncoder(
            ensure_ascii=ensure_ascii,
            allow_nan=allow_nan,
            sort_keys=False,
            separators=(item_sep, key_sep),
        ).encode

    def encode(self, data: D) -> BytesIO:
        return BytesIO(self._dumps(data).encode("utf-8"))

    def decode(self, buffer: BinaryIO) -> D:
        return json.load(buffer)
