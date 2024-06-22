__all__ = [
    "Json",
]

import json
from functools import lru_cache
from typing import Any, Callable

from iokit.state import State


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
    def __init__(
        self,
        data: Any,
        *,
        compact: bool = False,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        **kwargs: Any,
    ):
        dumps = json_dumps(compact=compact, ensure_ascii=ensure_ascii, allow_nan=allow_nan)
        data_ = dumps(data).encode("utf-8")
        super().__init__(data=data_, **kwargs)

    def load(self) -> Any:
        return json.load(self.data)
