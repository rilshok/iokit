__all__ = [
    "Jsonl",
]

from io import BytesIO
from typing import Any, Iterable

from jsonlines import Reader, Writer

from iokit.state import State

from .json import json_dumps


class Jsonl(State, suffix="jsonl"):
    def __init__(
        self,
        sequence: Iterable[dict[str, Any]],
        *,
        compact: bool = True,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        **kwargs: Any,
    ):
        buffer = BytesIO()
        dumps = json_dumps(compact=compact, ensure_ascii=ensure_ascii, allow_nan=allow_nan)
        with Writer(buffer, compact=compact, sort_keys=False, dumps=dumps) as writer:
            for item in sequence:
                writer.write(item)
        super().__init__(data=buffer, **kwargs)

    def load(self) -> list[Any]:
        with Reader(self.data) as reader:
            return list(reader)
