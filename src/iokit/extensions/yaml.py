__all__ = ["Yaml"]

from typing import Any

import yaml

from iokit.state import State


class Yaml(State, suffix="yaml"):
    def __init__(self, content: Any, /, **kwargs: Any):
        super().__init__(yaml.safe_dump(content).encode("utf-8"), **kwargs)

    def load(self) -> Any:
        return yaml.safe_load(self.buffer)
