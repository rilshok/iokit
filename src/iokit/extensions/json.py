import json
from functools import lru_cache
from typing import Any, Callable

from iokit import State


@lru_cache
def _json_dumps(
    *,
    compact: bool,
    ensure_ascii: bool,
    allow_nan: bool,
    sort_keys: bool,
) -> Callable[[Any], str]:
    item_sep = "," if compact else ", "
    key_sep = ":" if compact else ": "
    return json.JSONEncoder(
        ensure_ascii=ensure_ascii,
        allow_nan=allow_nan,
        sort_keys=sort_keys,
        separators=(item_sep, key_sep),
    ).encode

class Json(State, suffix="json"):
    def __init__(
        self,
        data: Any,
        compact: bool = False,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        sort_keys: bool = False,
        **kwargs: Any,
    ):
        dumps = _json_dumps(
            compact=compact,
            ensure_ascii=ensure_ascii,
            allow_nan=allow_nan,
            sort_keys=sort_keys,
        )
        data_ = dumps(data).encode("utf-8")
        super().__init__(data=data_, **kwargs)

    def load(self) -> Any:
        return json.load(self.data)
