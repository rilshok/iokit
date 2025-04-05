__all__ = ["Jsonl"]

from collections.abc import Iterable
from datetime import datetime
from io import BytesIO
from typing import Any

from jsonlines import Reader, Writer

from iokit.state import State, StateName

from .json import json_dumps


class Jsonl(State, suffix="jsonl"):
    def __init__(  # noqa: PLR0913
        self,
        data: Iterable[dict[str, Any]],
        /,
        name: str | StateName = "",
        *,
        compact: bool = True,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            dumps = json_dumps(compact=compact, ensure_ascii=ensure_ascii, allow_nan=allow_nan)
            with Writer(buffer, compact=compact, sort_keys=False, dumps=dumps) as writer:
                for item in data:
                    writer.write(item)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> list[Any]:
        with Reader(self.buffer) as reader:
            return list(reader)
