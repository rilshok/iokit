from datetime import datetime
from io import BytesIO
from typing import Any

import pytz
from humanize import naturalsize
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
    _suffix: str = ""
    _suffixes: tuple[str, ...] = ("",)

    def __init__(self, data: Payload, name: str | StateName = "", time: datetime | None = None):
        self._data = BytesIO(data) if isinstance(data, bytes) else data
        self._name = StateName.make(name, self._suffix)
        self._time = time or now()

    def __init_subclass__(
        cls,
        suffix: str | None = None,
        suffixes: tuple[str, ...] | None = None,
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

        cls._suffix = suffix
        cls._suffixes = suffixes

    @property
    def name(self) -> StateName:
        return self._name

    @name.setter
    def name(self, value: str | StateName) -> None:
        if isinstance(value, str):
            value = StateName(value)
        self._name = value

    @property
    def time(self) -> datetime:
        return self._time

    @time.setter
    def time(self, value: datetime) -> None:
        self._time = value

    @property
    def data(self) -> BytesIO:
        self._data.seek(0)
        return BytesIO(self._data.getvalue())

    @property
    def size(self) -> int:
        return self._data.getbuffer().nbytes

    def __repr__(self) -> str:
        size = naturalsize(self.size, gnu=True)
        return f"{self.name} ({size})"

    def cast(self) -> "State":
        suffix = self.name.suffix
        for klass in State.__subclasses__():
            if suffix in getattr(klass, "_suffixes"):
                break
        else:
            raise ValueError(f"Unknown state suffix {suffix}")
        state = klass.__new__(klass)
        setattr(state, "_data", self.data)
        setattr(state, "_name", self.name)
        setattr(state, "_time", self.time)
        return state

    def load(self) -> Any:
        if not self.name.suffix:
            return self.data.getvalue()
        return self.cast().load()
