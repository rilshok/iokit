"""Codec for YAML documents using safe parsing."""

__all__ = ["YamlCodec"]


from io import BytesIO
from typing import Any, BinaryIO

import yaml

from iokit.codec.base import Codec

D = dict[str, Any] | list[Any] | str


class YamlCodec(Codec[D]):
    """Convert between YAML and binary using safe parsing."""

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}()"

    def encode(self, data: D) -> BytesIO:
        """Dump `data` to YAML format."""
        return BytesIO(yaml.safe_dump(data).encode("utf-8"))

    def decode(self, buffer: BinaryIO) -> D:
        """Load YAML from `buffer`."""
        with buffer:
            return yaml.safe_load(buffer)
