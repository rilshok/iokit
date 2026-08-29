"""Codec for JSON documents with configurable formatting."""

import json
from io import BytesIO
from typing import Any, BinaryIO

from iokit.codec.base import Codec

D = dict[str, Any] | list[Any] | str


class JsonCodec(Codec[D]):
    """Convert between JSON and binary with formatting options."""

    def __init__(
        self,
        *,
        compact: bool = False,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
    ) -> None:
        """Initialize codec with JSON serialization options.

        Args:
            compact: No space after separators (default: readable spacing).
            ensure_ascii: Escape non-ASCII characters.
            allow_nan: Permit `NaN`, `Infinity`, `-Infinity` in output.

        """
        self._compact = compact
        self._ensure_ascii = ensure_ascii
        self._allow_nan = allow_nan
        item_sep = "," if compact else ", "
        key_sep = ":" if compact else ": "
        self._encode = json.JSONEncoder(
            ensure_ascii=ensure_ascii,
            allow_nan=allow_nan,
            sort_keys=False,
            separators=(item_sep, key_sep),
        ).encode

    def __repr__(self) -> str:
        """Return codec representation with all options."""
        return (
            f"{type(self).__name__}("
            f"compact={self._compact}, "
            f"ensure_ascii={self._ensure_ascii}, "
            f"allow_nan={self._allow_nan}"
            ")"
        )

    def encode(self, data: D) -> BytesIO:
        """Serialize `data` to JSON bytes."""
        return BytesIO(self._encode(data).encode("utf-8"))

    def decode(self, buffer: BinaryIO) -> D:
        """Parse JSON from `buffer`."""
        with buffer:
            return json.load(buffer)
