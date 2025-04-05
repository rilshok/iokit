__all__ = ["Json"]

import json
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from typing import Any

from iokit.state import State, StateName


@lru_cache
def json_dumps(
    *,
    compact: bool,
    ensure_ascii: bool,
    allow_nan: bool,
) -> Callable[[Any], str]:
    item_sep = "," if compact else ", "
    key_sep = ":" if compact else ": "
    return json.JSONEncoder(
        ensure_ascii=ensure_ascii,
        allow_nan=allow_nan,
        sort_keys=False,
        separators=(item_sep, key_sep),
    ).encode


class Json(State, suffix="json"):
    def __init__(  # noqa: PLR0913
        self,
        data: object,
        /,
        name: str | StateName = "",
        *,
        compact: bool = False,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        time: datetime | None = None,
    ) -> None:
        dumps = json_dumps(compact=compact, ensure_ascii=ensure_ascii, allow_nan=allow_nan)
        super().__init__(dumps(data).encode("utf-8"), name=name, time=time)

    def load(self) -> object:
        return json.load(self.buffer)
