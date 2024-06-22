from datetime import datetime
from io import BytesIO

import pytz
from typing_extensions import Self

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

    @classmethod
    def make(cls, stem: "str | StateName", suffix: str) -> Self:
        if suffix:
            return cls(f"{stem}.{suffix}")
        return cls(str(stem))


class State:
    suffix: str = ""
    suffixes: tuple[str, ...] = ("",)

    def __init__(self, data: Payload, stem: str | StateName = "", mtime: datetime | None = None):
        self._data = BytesIO(data) if isinstance(data, bytes) else data
        self._name = StateName.make(stem, self.suffix)
        self._mtime = mtime or now()

    def __init_subclass__(
        cls, suffix: str | None = None, suffixes: tuple[str, ...] | None = None
    ) -> None:
        if suffix is None and suffixes is not None:
            if len(suffixes) == 0:
                raise ValueError("State subclasses must define at least one suffix")
            suffix = suffixes[0]
        if suffix is not None and suffixes is None:
            suffixes = (suffix,)

        if suffix is not None and suffixes is not None:
            if suffix not in suffixes:
                suffixes = (suffix, *suffixes)

        if suffix is None or suffixes is None:
            raise ValueError("State subclasses must define a suffix or suffixes")

        cls.suffix = suffix
        cls.suffixes = suffixes

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
