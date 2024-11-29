__all__ = ["Csv", "Tsv"]

from io import BytesIO
from typing import Any

from pandas import DataFrame, read_csv

from iokit.state import State


class Csv(State, suffix="csv"):
    def __init__(self, content: DataFrame, /, *, index: bool = False, **kwargs: Any):
        with BytesIO() as buffer:
            content.to_csv(buffer, index=index)
            super().__init__(buffer.getvalue(), **kwargs)

    def load(self) -> DataFrame:
        return read_csv(self.buffer)


class Tsv(State, suffix="tsv"):
    def __init__(self, content: DataFrame, /, *, index: bool = False, **kwargs: Any):
        with BytesIO() as buffer:
            content.to_csv(buffer, sep="\t", index=index)
            super().__init__(buffer.getvalue(), **kwargs)

    def load(self) -> DataFrame:
        return read_csv(self.buffer, sep="\t")
