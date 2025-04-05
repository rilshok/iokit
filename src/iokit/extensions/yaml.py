__all__ = ["Yaml"]

from datetime import datetime

import yaml

from iokit.state import State, StateName


class Yaml(State, suffix="yaml"):
    def __init__(
        self,
        data: object,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        super().__init__(yaml.safe_dump(data).encode("utf-8"), name=name, time=time)

    def load(self) -> object:
        return yaml.safe_load(self.buffer)
