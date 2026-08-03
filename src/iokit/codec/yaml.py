__all__ = ["YamlCodec"]


from io import BytesIO
from typing import Any, BinaryIO

import yaml

from iokit.utils.state_new import Codec

D = dict[str, Any] | list[Any] | str


class YamlCodec(Codec[D]):
    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def encode(self, data: D) -> BytesIO:
        return BytesIO(yaml.safe_dump(data).encode("utf-8"))

    def decode(self, buffer: BinaryIO) -> D:
        with buffer:
            return yaml.safe_load(buffer)
