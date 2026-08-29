"""Codec for JSON Lines (newline-delimited JSON)."""

__all__ = ["JsonlCodec"]

import json
from io import BytesIO
from typing import Any, BinaryIO

from jsonlines import Reader, Writer

from iokit.codec.base import Codec

D = list[Any]


class JsonlCodec(Codec[D]):
    """Convert lists to/from JSON Lines format."""

    def __init__(
        self,
        *,
        compact: bool = True,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
    ) -> None:
        """Initialize codec with JSON options.

        Args:
            compact: Compact format (no spaces).
            ensure_ascii: Escape non-ASCII.
            allow_nan: Allow `NaN` and `Infinity`.

        """
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
        """Return codec representation."""
        return (
            f"{type(self).__name__}("
            f"compact={self._compact}, "
            f"ensure_ascii={self._ensure_ascii}, "
            f"allow_nan={self._allow_nan}"
            ")"
        )

    def encode(self, data: D) -> BytesIO:
        """Write each item in `data` as a separate JSON line."""
        buffer = BytesIO()
        with Writer(buffer, compact=self._compact, sort_keys=False, dumps=self._dumps) as writer:
            for item in data:
                writer.write(item)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> D:
        """Read and parse JSON Lines from `buffer` into a list of objects."""
        with buffer, Reader(buffer) as reader:
            return list(reader)
