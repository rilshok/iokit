__all__ = [
    "Yaml",
]

from typing import Any

import yaml

from iokit.state import State


class Yaml(State, suffix="yaml"):
    def __init__(self, data: Any, **kwargs: Any):
        data = yaml.safe_dump(data).encode("utf-8")
        super().__init__(data=data, **kwargs)

    def load(self) -> Any:
        return yaml.safe_load(self.data)
