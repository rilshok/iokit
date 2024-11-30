__all__ = ["Csv", "Tsv"]

from datetime import datetime
from io import BytesIO

from pandas import DataFrame, read_csv

from iokit.state import State, StateName


class Csv(State, suffix="csv"):
    def __init__(
        self,
        data: DataFrame,
        /,
        name: str | StateName = "",
        *,
        index: bool = False,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            data.to_csv(buffer, index=index)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> DataFrame:
        return read_csv(self.buffer)


class Tsv(State, suffix="tsv"):
    def __init__(
        self,
        data: DataFrame,
        /,
        name: str | StateName = "",
        *,
        index: bool = False,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            data.to_csv(buffer, sep="\t", index=index)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> DataFrame:
        return read_csv(self.buffer, sep="\t")
