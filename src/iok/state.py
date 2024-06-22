from datetime import datetime
from io import BytesIO

import pytz

Payload = BytesIO | bytes


def now() -> datetime:
    return datetime.now(pytz.utc)


class StateName:
    def __init__(self, name: str):
        self._name = name

    @property
    def stem(self) -> str:
        split = self._name.split(sep=".", maxsplit=1)
        return split[0]

    @stem.setter
    def stem(self, new: str) -> None:
        suffix = ".".join(self.suffixes)
        self._name = f"{new}.{suffix}"

    @property
    def suffix(self) -> str:
        split = self._name.rsplit(sep=".", maxsplit=1)
        if len(split) == 2:
            return f"{split[-1]}"
        raise ValueError(f"State name '{self._name}' does not have a suffix")

    @property
    def suffixes(self) -> tuple[str, ...]:
        split = self._name.split(sep=".")[1:]
        return tuple(f"{s}" for s in split)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self._name


class State:
    def __init__(self, data: Payload, name: str | StateName = "", mtime: datetime | None = None):
        self._data = BytesIO(data) if isinstance(data, bytes) else data
        self._name = StateName(name) if isinstance(name, str) else name
        self._mtime = mtime or now()

    @property
    def name(self) -> StateName:
        return self._name

    @name.setter
    def name(self, value: str | StateName) -> None:
        if isinstance(value, str):
            value = StateName(value)
        self._name = value

    @property
    def mtime(self) -> datetime:
        return self._mtime

    @mtime.setter
    def mtime(self, value: datetime) -> None:
        self._mtime = value
