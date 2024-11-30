__all__ = ["Yaml"]

from datetime import datetime
from typing import Any

import yaml

from iokit.state import State, StateName


class Yaml(State, suffix="yaml"):
    def __init__(
        self,
        data: Any,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        super().__init__(yaml.safe_dump(data).encode("utf-8"), name=name, time=time)

    def load(self) -> Any:
        return yaml.safe_load(self.buffer)
